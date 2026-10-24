"""The MCP executor can run on the Deadline farm (DEADLINE_ROUTE_RUNS=1); off, it is untouched."""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenty_core.tools import deadline_farm as df
from agenty_core.utils import farm_run
from src import executor

PROMPT = {"1": {"class_type": "KSampler", "inputs": {"seed": 1}},
          "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "filename_prefix": "x"}}}
_REAL_SLEEP = asyncio.sleep


async def _lines(gen):
    return [x async for x in gen]


class FarmRouting(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        self.wf = self.dir / "wf.json"
        self.wf.write_text(json.dumps(PROMPT))
        self.out = self.dir / "o_t0000.png"
        self.out.write_bytes(b"png")
        self.enterContext(mock.patch.dict(os.environ, {"DEADLINE_ROUTE_RUNS": "", "DEADLINE_FETCH_DIR": ""}))

    def test_a_farm_reference_is_streamed_by_the_farm(self):
        gen = executor._job_stream("farm:J1", "c")
        self.assertIn("stream", gen.__qualname__)
        asyncio.run(gen.aclose())

    def test_no_partner_settle_for_a_farm_job(self):
        self.assertEqual(asyncio.run(executor._settle_partner("farm:J1")), "")

    def test_submission_is_routed_after_the_cost_gate_and_never_posts_to_comfyui(self):
        client = mock.Mock()
        with mock.patch.dict(os.environ, {"DEADLINE_ROUTE_RUNS": "1"}), \
                mock.patch("agenty_core.partner_credits.gate_submission", return_value=0), \
                mock.patch("src.utils.comfyui_client.get_client", return_value=client), \
                mock.patch.object(farm_run, "submit", return_value="farm:J1") as sub:
            ref = executor._submit_workflow(str(self.wf), client_id="c")
        self.assertEqual(ref, "farm:J1")
        client.post.assert_not_called()
        self.assertEqual(sub.call_args.kwargs["name"], "wf")

    def test_off_it_posts_to_comfyui_as_before(self):
        client = mock.Mock()
        client.api_key = ""
        client.post.return_value = {"prompt_id": "pid1"}
        with mock.patch("agenty_core.partner_credits.gate_submission", return_value=0), \
                mock.patch("agenty_core.partner_credits.track"), \
                mock.patch("src.utils.comfyui_client.get_client", return_value=client), \
                mock.patch.object(farm_run, "submit") as sub:
            ref = executor._submit_workflow(str(self.wf), client_id="c")
        self.assertEqual(ref, "pid1")
        sub.assert_not_called()

    def test_a_routed_run_delivers_the_files(self):
        states = iter([{"state": "Rendering", "progress": 0.4, "tasks": {"completed": 0, "total": 1}},
                       {"state": "Completed", "outputs": [str(self.out)]}])
        collected: list = []
        with mock.patch.object(executor, "_submit_workflow", return_value="farm:J1"), \
                mock.patch.object(df, "job_status", side_effect=lambda j, w=0: next(states)), \
                mock.patch.object(farm_run.asyncio, "sleep", new=lambda s: _REAL_SLEEP(0)):
            lines = asyncio.run(_lines(executor.execute_workflow(
                str(self.wf), "{}", collected_paths=collected, verbose=False)))
        text = "\n".join(l for l in lines if isinstance(l, str))
        self.assertIn("rendering", text)
        self.assertEqual(collected, [str(self.out)])


if __name__ == "__main__":
    unittest.main()
