"""partner_run is offered by the MCP server and builds through the shared layer.

    python -m unittest tests.test_partner_run
"""
import asyncio
import json
import unittest
from unittest import mock

from src import tools as T
from src.tools import execution as E


class Offered(unittest.TestCase):
    def test_it_is_in_the_server_tool_list(self):
        from src import mcp_server
        self.assertIn(T.partner_run, mcp_server._TOOLS)

    def test_run_variants_is_offered_too(self):
        from src import mcp_server
        self.assertIn(T.run_variants, mcp_server._TOOLS)

    def test_run_variants_submits_every_ready_copy_in_one_batch(self):
        calls = []

        async def fake_batch(paths, brief, **kw):
            calls.append(list(paths))
            kw["collected_paths"].extend(p + ".png" for p in paths)
            yield "queued"

        prep = {"status": "ok", "ready": ["a.json", "b.json"],
                "variants": [{"index": 1, "label": "x", "workflow_path": "a.json", "status": "ok", "problems": []},
                             {"index": 2, "label": "y", "workflow_path": "b.json", "status": "ok", "problems": []}]}
        with mock.patch("agenty_core.tools.variants.prepare_variants", return_value=prep),              mock.patch.object(E, "_stream_batch", fake_batch),              mock.patch.object(E, "_image_blocks_for_outputs", return_value=[]):
            out = asyncio.run(E.run_variants("base.json", [{}, {}]))
        self.assertEqual(calls, [["a.json", "b.json"]])
        self.assertIn("a.json.png", out[0])

    def test_a_failed_build_is_returned_not_run(self):
        with mock.patch("agenty_core.tools.partner_run.prepare_partner_workflow",
                        return_value={"status": "error", "errors": ["nope"]}), \
             mock.patch.object(E, "_stream_one") as run:
            out = asyncio.run(E.partner_run("X"))
        self.assertEqual(json.loads(out[0])["status"], "error")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
