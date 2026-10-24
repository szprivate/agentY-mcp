"""The Claude Code plugin package: manifests, versions, skills mirror, agents/commands.

    python -m unittest tests.test_plugin_package
"""
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIBLING_SYNC = ROOT.parent / "agentY" / "scripts" / "sync_plugin_skills.py"


def _json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _digest(folder: Path) -> str:
    """Same hash as agentY/scripts/sync_plugin_skills.py (line endings do not count)."""
    h = hashlib.sha256()
    files = sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    for f in files:
        h.update(f.relative_to(folder).as_posix().encode() + b"\0" + f.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


class Manifests(unittest.TestCase):
    def test_plugin_json(self):
        p = _json(".claude-plugin/plugin.json")
        self.assertEqual(p["name"], "agenty")
        self.assertRegex(p["version"], r"^\d+\.\d+\.\d+$")

    def test_marketplace_points_at_this_repo_and_the_plugin_name(self):
        m = _json(".claude-plugin/marketplace.json")
        entry = m["plugins"][0]
        self.assertEqual(entry["name"], _json(".claude-plugin/plugin.json")["name"])
        self.assertEqual(entry["source"], "./")
        self.assertTrue((ROOT / "skills").is_dir() and (ROOT / "agents").is_dir())

    def test_versions_agree(self):
        v = _json(".claude-plugin/plugin.json")["version"]
        self.assertEqual(_json(".claude-plugin/marketplace.json")["plugins"][0]["version"], v)
        self.assertEqual(_json("manifest.json")["version"], v)

    def test_mcp_json_starts_the_server_from_the_plugin_root(self):
        s = _json(".mcp.json")["mcpServers"]["agentY"]
        self.assertEqual(s["command"], "uv")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/.venv", s["args"])
        self.assertEqual(s["args"][-2:], ["-m", "src"])

    def test_mcpb_manifest_tools_exist(self):
        from src import mcp_server
        offered = {t.__name__ for t in mcp_server._TOOLS}
        listed = {t["name"] for t in _json("manifest.json")["tools"]}
        self.assertFalse(listed - offered, "manifest.json lists tools the server does not offer")
        self.assertFalse(offered - listed, "manifest.json is missing tools - run scripts/update_manifest.py")


class SkillsMirror(unittest.TestCase):
    def test_skills_match_the_sync_manifest(self):
        """skills/ was not edited by hand and nothing is missing (offline check)."""
        want = _json("skills.sync.json")["skills"]
        have = {d.name for d in (ROOT / "skills").iterdir() if d.is_dir()}
        self.assertEqual(have, set(want), "skills/ and skills.sync.json list different skills")
        for name, info in want.items():
            self.assertEqual(_digest(ROOT / "skills" / name), info["sha256"],
                             f"skills/{name} differs from the sync - run agentY/scripts/sync_plugin_skills.py")

    @unittest.skipUnless(SIBLING_SYNC.is_file(), "agentY is not next to this repo")
    def test_skills_match_agentY(self):
        spec = importlib.util.spec_from_file_location("sync_plugin_skills", SIBLING_SYNC)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cfg = mod.load_config()
        p = mod.changes(SIBLING_SYNC.parent.parent / "skills", ROOT, cfg["exclude"])
        self.assertTrue(mod.is_clean(p), "the plugin skills are stale: " + mod.describe(p)
                        + " - run agentY/scripts/sync_plugin_skills.py and commit")

    def test_git_tracks_the_same_folder_names_as_the_disk(self):
        """On Windows/macOS git keeps the old case of a renamed folder; Linux would then miss the skill."""
        import shutil
        import subprocess
        if not shutil.which("git"):
            self.skipTest("no git")
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "skills"], capture_output=True, text=True)
        if out.returncode != 0:
            self.skipTest("not a git checkout")
        tracked = {line.split("/")[1] for line in out.stdout.splitlines() if line.count("/") >= 2}
        self.assertEqual(tracked, {d.name for d in (ROOT / "skills").iterdir() if d.is_dir()})

    def test_every_skill_has_matching_folder_and_name(self):
        for d in (ROOT / "skills").iterdir():
            if d.is_dir():
                text = (d / "SKILL.md").read_text(encoding="utf-8-sig")
                self.assertRegex(text, rf"(?m)^name:\s*{re.escape(d.name)}\s*$", d.name)


class AgentsAndCommands(unittest.TestCase):
    # snake_case words in the prose that are JSON fields, not tools
    FIELDS = {"server_errors", "workflow_path", "output_path", "input_image_count", "output_dir", "used_as", "fix_plan"}

    def test_tool_names_in_agents_and_commands_exist(self):
        from src import mcp_server
        offered = {t.__name__ for t in mcp_server._TOOLS}
        for f in [*(ROOT / "agents").glob("*.md"), *(ROOT / "commands").glob("*.md")]:
            for token in set(re.findall(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`", f.read_text(encoding="utf-8"))):
                if token in self.FIELDS:
                    continue
                self.assertIn(token, offered, f"{f.name} names `{token}`, which the server does not offer")

    def test_skills_named_in_agents_and_commands_exist(self):
        have = {d.name for d in (ROOT / "skills").iterdir() if d.is_dir()}
        for f in [*(ROOT / "agents").glob("*.md"), *(ROOT / "commands").glob("*.md")]:
            text = f.read_text(encoding="utf-8")
            for token in re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`(?: skill)?", text):
                if token in {"query-templates", "assemble-workflow", "error-checker", "reference-scout", "agenty-generate"}:
                    continue
                self.assertIn(token, have, f"{f.name} names the skill `{token}`, which is not in skills/")

    def test_agent_frontmatter(self):
        for f in (ROOT / "agents").glob("*.md"):
            text = f.read_text(encoding="utf-8")
            self.assertRegex(text, rf"(?m)^name:\s*{re.escape(f.stem)}\s*$", f.name)
            self.assertRegex(text, r"(?m)^model:\s*(haiku|sonnet|opus|inherit)\s*$", f.name)


if __name__ == "__main__":
    unittest.main()
