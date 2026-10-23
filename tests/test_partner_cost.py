"""agentY-mcp: paid (partner) nodes are priced and gated before anything is queued.

Offline: schemas and balance are stubs; ComfyUI is never contacted.
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agenty_core import partner_credits as pc

BADGE = {"engine": "jsonata", "depends_on": {"widgets": [{"name": "n", "type": "INT"}], "inputs": [],
                                             "input_groups": []},
         "expr": '{"type":"usd","usd": widgets.n * 0.5}'}
INFO = {"PaidNode": {"price_badge": BADGE}, "KSampler": {"price_badge": None}}


def write(n=None):
    wf = ({"1": {"class_type": "PaidNode", "inputs": {"n": n}}} if n is not None
          else {"1": {"class_type": "KSampler", "inputs": {}}})
    f = Path(tempfile.mkdtemp()) / "w.json"
    f.write_text(json.dumps(wf), encoding="utf-8")
    return str(f)


class Gate(unittest.TestCase):
    def setUp(self):
        pc.clear_caches()
        self.calls = 0
        self.cents = 10000
        pc._info_provider = lambda ct: INFO.get(ct)
        pc._http_get = self._bal
        pc._sleep = lambda s: None
        self._log, pc._log = pc._log, lambda e: None
        pc._confirmed_paths.clear()
        pc._inflight.clear()

    def _bal(self, url, headers):
        self.calls += 1
        return {"effective_balance_cents": self.cents, "prepaid_balance_cents": self.cents}

    def tearDown(self):
        pc._http_get = pc._info_provider = pc._threshold_provider = None
        pc._sleep = __import__("time").sleep
        pc._log = self._log
        pc.clear_caches()

    def test_tools_are_exposed(self):
        from src import mcp_server  # noqa: F401
        from src.tools import estimate_workflow_cost
        self.assertTrue(callable(estimate_workflow_cost))
        src = (Path(__file__).parent.parent / "src" / "mcp_server.py").read_text(encoding="utf-8")
        self.assertIn("T.estimate_workflow_cost", src)

    def test_execute_workflow_asks_then_proceeds_with_confirmation(self):
        from src.tools import execution
        path = write(4)                                           # $2.00
        got = asyncio.run(execution.execute_workflow(path))
        self.assertEqual(json.loads(got[0])["error_kind"], "confirm_cost")
        ran = []

        async def fake(wf, brief, **kw):
            ran.append(wf)
            yield "ok"
        orig = execution._stream_one
        execution._stream_one = fake
        try:
            asyncio.run(execution.execute_workflow(path, confirm_cost=True))
        finally:
            execution._stream_one = orig
        self.assertEqual(ran, [path])

    def test_batch_is_judged_on_the_sum(self):
        from src.tools import execution
        paths = [write(1), write(1), write(1)]                    # 3 x $0.50 = $1.50
        got = asyncio.run(execution.execute_workflows_batch(paths))
        self.assertEqual(json.loads(got[0])["error_kind"], "confirm_cost")

    def test_local_graph_makes_no_balance_call(self):
        from src.tools import execution
        self.assertIsNone(execution._cost_gate([write()], False))
        self.assertEqual(self.calls, 0)

    def test_executor_submission_is_gated_and_tracked(self):
        from src import executor
        from agenty_core.utils import comfyui_client as C
        posts = []

        class Client:
            api_key = ""

            def post(self, path, json_data=None, **_):
                posts.append(path)
                return {"prompt_id": "pid"}
        orig = C.get_client
        import src.utils.comfyui_client as SC
        o2 = getattr(SC, "get_client", None)
        C.get_client = lambda: Client()
        SC.get_client = lambda: Client()
        try:
            with self.assertRaises(pc.CostGateError):
                executor._submit_workflow(write(4))
            self.assertEqual(posts, [])
            self.assertEqual(executor._submit_workflow(write(1)), "pid")      # $0.50 runs
            self.assertIn("pid", pc._inflight)
            self.cents = 10000 - 50
            line = asyncio.run(executor._settle_partner("pid"))
            self.assertIn("0.50", line)
        finally:
            C.get_client = orig
            if o2 is not None:
                SC.get_client = o2


if __name__ == "__main__":
    unittest.main()
