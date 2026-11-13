"""Recreate shots with changes: offered by the MCP server, each shot run through its executor.

    python -m unittest tests.test_regenerate_offered
"""
import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenty_core.tools import regenerate as rg
from agenty_core.utils import provenance as pv
from src import tools as T
from src.tools import execution as E

GRAPH = {
    "3": {"class_type": "KSampler", "inputs": {"seed": 5, "steps": 20, "cfg": 7.0, "sampler_name": "euler",
                                               "scheduler": "normal", "denoise": 1.0, "model": ["4", 0],
                                               "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
    "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd15.safetensors"}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red barn in a field", "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["4", 1]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["3", 0], "filename_prefix": "barn"}},
}


class Offered(unittest.TestCase):
    def test_the_three_tools_are_in_the_server_list(self):
        from src import mcp_server
        for fn in (T.recreatable_params, T.regenerate_from_source, T.swap_in_takes):
            self.assertIn(fn, mcp_server._TOOLS)
        self.assertIs(T.regenerate_from_source, E.regenerate_from_source)
        self.assertIn("EXACTLY", E.regenerate_from_source.__doc__)

    def test_animate_character_is_offered(self):
        """The character-animation skill names animate_character; it carries the pose / restyle / video options."""
        from src import mcp_server
        self.assertIn(T.animate_character, mcp_server._TOOLS)
        doc = T.animate_character.__doc__ or ""
        for word in ("pose_presets", "restyle", "lipsync"):
            self.assertIn(word, doc)

    def test_edit_cut_is_offered_too(self):
        """The cut in the viewer's Edit panel: read it, lay a voice-over or a clip at a time, trim, remove."""
        from src import mcp_server
        self.assertIn(T.edit_cut, mcp_server._TOOLS)

    def test_edit_image_and_file_dependencies_are_offered(self):
        """Paint (the show-in-viewer skill sends the agent to edit_image) and the file dependencies."""
        from src import mcp_server
        self.assertIn(T.edit_image, mcp_server._TOOLS)
        self.assertIn(T.file_dependencies, mcp_server._TOOLS)
        self.assertIn("snapshot", T.edit_image.__doc__)
        names = {t["name"] for t in json.loads(Path("manifest.json").read_text(encoding="utf-8-sig"))["tools"]}
        self.assertTrue({"edit_image", "file_dependencies"} <= names)

    def test_the_comp_tools_are_offered(self):
        """The viewer's Comp space: build a comp, render its Write nodes here or on the farm."""
        from src import mcp_server
        self.assertIn(T.edit_comp, mcp_server._TOOLS)
        self.assertIn(T.render_comp, mcp_server._TOOLS)
        names = {t["name"] for t in json.loads(Path("manifest.json").read_text(encoding="utf-8-sig"))["tools"]}
        self.assertTrue({"edit_comp", "render_comp"} <= names)

    def test_the_manifest_lists_them(self):
        names = {t["name"] for t in json.loads(Path("manifest.json").read_text(encoding="utf-8-sig"))["tools"]}
        self.assertTrue({"recreatable_params", "regenerate_from_source", "swap_in_takes"} <= names)

    def test_the_executor_records_provenance(self):
        import inspect
        from src import executor
        self.assertIn("_prov.capture(saved_paths, history, prompt_id, workflow_path",
                      inspect.getsource(executor._process_completed_job))


class Runs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.shot = self.tmp / "barn_00001_.png"
        self.shot.write_bytes(b"old")
        pv.write(self.shot, GRAPH, prompt_id="p0", output_node="9")

    def test_dry_run_runs_nothing_and_the_real_run_goes_through_the_executor(self):
        calls = []

        async def fake_stream(workflow_path, brief, **kw):
            g = json.loads(Path(workflow_path).read_text(encoding="utf-8"))
            calls.append(g["3"]["inputs"]["seed"])
            out = self.tmp / "out" / "barn_00002_.png"
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(b"new")
            pv.capture([out], {"p1": {"prompt": [1, "p1", g],
                                      "outputs": {"9": {"images": [{"filename": out.name}]}}}}, "p1",
                       background=False)
            kw["collected_paths"].append(str(out))
            yield "done"

        with mock.patch.object(E, "_stream_one", fake_stream), \
                mock.patch.object(E, "_cost_gate", return_value=None), \
                mock.patch.object(rg, "_validation_error", return_value=""):
            dry = json.loads(asyncio.run(E.regenerate_from_source([str(self.shot)], [{"param": "seed", "value": 9}])))
            self.assertEqual((dry["dry_run"], calls), (True, []))
            out = json.loads(asyncio.run(E.regenerate_from_source([str(self.shot)], [{"param": "seed", "value": 9}],
                                                                  dry_run=False)))
        self.assertEqual(calls, [9])
        r = out["results"][0]
        self.assertEqual((r["status"], Path(r["new_file"]).name, r["prompt_id"]), ("done", "barn_00001_v002.png", "p1"))
        self.assertEqual(pv.provenance_of(r["new_file"])["graph"]["3"]["inputs"]["seed"], 9)
        self.assertIsNone(rg._runner)

    def test_a_cost_refusal_is_the_shots_answer(self):
        refusal = [json.dumps({"status": "error", "error_kind": "confirm_cost", "error": "costs $3.00"})]
        with mock.patch.object(E, "_cost_gate", return_value=refusal), \
                mock.patch.object(rg, "_validation_error", return_value=""):
            out = json.loads(asyncio.run(E.regenerate_from_source([str(self.shot)], [{"param": "steps", "value": 30}],
                                                                  dry_run=False)))
        self.assertEqual(out["results"][0]["error_kind"], "confirm_cost")
        self.assertIn("confirm_cost=True", out["hint"])


if __name__ == "__main__":
    unittest.main()
