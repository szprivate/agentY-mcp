import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from src import sync_deps


class SyncDepsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.req = self.tmp / "requirements.txt"
        self.core = self.tmp / "pyproject.toml"
        self.req.write_text("mcp\n")
        self.core.write_text("a\n")
        self.files = (self.req, self.core)

    def test_fingerprint_changes_with_core_and_ignores_crlf(self):
        a = sync_deps.fingerprint(self.files)
        self.core.write_bytes(b"a\r\n")
        self.assertEqual(a, sync_deps.fingerprint(self.files))
        self.core.write_text("a\nOpenEXR\n")
        self.assertNotEqual(a, sync_deps.fingerprint(self.files))

    def test_reasons(self):
        self.assertEqual(sync_deps.reasons(None, "x", []), [])
        self.assertEqual(sync_deps.reasons("x", "x", []), [])
        self.assertEqual(len(sync_deps.reasons("old", "new", [])), 1)
        self.assertIn("OpenEXR", sync_deps.reasons("x", "x", ["OpenEXR"])[0])

    def _run(self, stamp, missing, returncode=0):
        wrote = []
        proc = mock.Mock(returncode=returncode, stdout=b"out line\n")
        with mock.patch.object(sync_deps, "fingerprint", return_value="new"), \
             mock.patch.object(sync_deps, "read_stamp", return_value=stamp), \
             mock.patch.object(sync_deps, "missing_required", return_value=missing), \
             mock.patch.object(sync_deps, "write_stamp", side_effect=wrote.append), \
             mock.patch.object(sync_deps.subprocess, "run", return_value=proc) as run:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), mock.patch.object(sync_deps.sys, "stderr", err):
                result = sync_deps.sync()
        return result, run, wrote, out.getvalue(), err.getvalue()

    def test_unchanged_does_nothing(self):
        result, run, wrote, out, _ = self._run("new", [])
        self.assertFalse(result)
        run.assert_not_called()
        self.assertEqual(out, "")

    def test_first_sight_only_stamps(self):
        _, run, wrote, _, _ = self._run(None, [])
        run.assert_not_called()
        self.assertEqual(wrote, ["new"])

    def test_changed_installs_to_stderr_and_stamps(self):
        result, run, wrote, out, err = self._run("old", [])
        self.assertTrue(result)
        run.assert_called_once()
        self.assertEqual(wrote, ["new"])
        self.assertEqual(out, "")
        self.assertIn("out line", err)

    def test_missing_triggers_install(self):
        result, run, *_ = self._run("new", ["OpenEXR"])
        self.assertTrue(result)
        run.assert_called_once()

    def test_failed_install_does_not_stamp_or_raise(self):
        result, _, wrote, out, err = self._run("old", [], returncode=1)
        self.assertFalse(result)
        self.assertEqual(wrote, [])
        self.assertEqual(out, "")
        self.assertIn("starting anyway", err)

    def test_ensure_skips_unmanaged_and_swallows_errors(self):
        with mock.patch.object(sync_deps, "managed_venv", return_value=False), \
             mock.patch.object(sync_deps, "sync") as s:
            sync_deps.ensure()
            s.assert_not_called()
        with mock.patch.object(sync_deps, "managed_venv", return_value=True), \
             mock.patch.object(sync_deps, "sync", side_effect=RuntimeError("x")):
            sync_deps.ensure()

    def test_install_command_names_the_venv_python(self):
        with mock.patch.object(sync_deps.shutil, "which", return_value=None):
            self.assertEqual(sync_deps.install_command("py")[:3], ["py", "-m", "pip"])
        with mock.patch.object(sync_deps.shutil, "which", return_value="uv"):
            self.assertIn("--python", sync_deps.install_command("py"))


if __name__ == "__main__":
    unittest.main()
