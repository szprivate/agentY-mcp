"""The client for a running agentY host, against a fake host on a real socket.

The fake speaks the turn API (POST /agentY/turns, GET /agentY/turns/<id>?wait=)
and enforces the session-token header the real host requires.
"""
import asyncio
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.utils import agenty_host_client as host

TOKEN = "t" * 32


class FakeHost(BaseHTTPRequestHandler):
    polls = {}
    sent = []

    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _auth(self):
        if self.headers.get(host.TOKEN_HEADER) != TOKEN:
            self._send(403, {"error": "missing or stale session token"})
            return False
        return True

    def do_POST(self):
        if not self._auth():
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        FakeHost.sent.append((self.path, body))
        if self.path == "/agentY/turns":
            if body.get("message") == "busy":
                return self._send(409, {"error": "already running"})
            tid = "slow" if body.get("message") == "slow" else "t1"
            return self._send(202, {"turn_id": tid, "conversation": body.get("conversation") or "c1",
                                    "status": "running"})
        self._send(200, {"ok": True})

    def do_GET(self):
        if not self._auth():
            return
        if self.path.startswith("/agentY/turns/"):
            rid = self.path.split("/")[3].split("?")[0]
            n = FakeHost.polls[rid] = FakeHost.polls.get(rid, 0) + 1
            if rid == "slow":
                return self._send(200, {"turn_id": rid, "status": "running"})
            if rid == "ask":
                return self._send(200, {"turn_id": rid, "status": "waiting", "waiting": {"prompt": "ok?"}})
            if n < 2:
                return self._send(200, {"turn_id": rid, "status": "running"})
            return self._send(200, {"turn_id": rid, "status": "done", "reply": "hello", "files": []})
        if self.path == "/agentY/threads":
            return self._send(200, [{"id": "c1", "title": "A", "running": False, "junk": 1}])
        self._send(404, {"error": "no"})


class ClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeHost)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls._env = dict(os.environ)
        os.environ["AGENTY_HOST_URL"] = f"http://127.0.0.1:{cls.srv.server_port}"
        os.environ["AGENTY_SESSION_TOKEN"] = TOKEN

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        os.environ.clear()
        os.environ.update(cls._env)

    def setUp(self):
        FakeHost.polls.clear()
        FakeHost.sent.clear()

    def test_wait_follows_to_the_end(self):
        res = host.run_turn("hi", conversation="c9", title="T")
        self.assertEqual(res["status"], "done")
        self.assertEqual(res["reply"], "hello")
        self.assertEqual(FakeHost.sent[0][1]["conversation"], "c9")

    def test_canvas_target_is_sent_and_omitted_by_default(self):
        host.run_turn("hi", wait=False, canvas="none")
        self.assertEqual(FakeHost.sent[-1][1]["canvas"], "none")
        host.run_turn("hi", wait=False)
        self.assertNotIn("canvas", FakeHost.sent[-1][1])

    def test_no_wait_returns_the_id(self):
        res = host.run_turn("hi", wait=False)
        self.assertEqual(res["turn_id"], "t1")
        self.assertEqual(FakeHost.polls, {})

    def test_waiting_returns_the_question(self):
        FakeHost.polls["ask"] = 5
        self.assertEqual(host.turn_status("ask")["status"], "waiting")

    def test_timeout_leaves_the_turn_running(self):
        res = host.run_turn("slow", timeout_s=1)
        self.assertTrue(res["timed_out"])
        self.assertEqual(res["status"], "running")

    def test_attachments_are_made_absolute(self):
        host.start_turn("hi", attachments=["rel.png"])
        self.assertTrue(os.path.isabs(FakeHost.sent[0][1]["attachments"][0]))

    def test_a_wrong_token_says_how_to_fix_it(self):
        os.environ["AGENTY_SESSION_TOKEN"] = "x" * 32
        try:
            with self.assertRaises(host.HostError) as cm:
                host.start_turn("hi")
            self.assertIn("AGENTY_SESSION_TOKEN", str(cm.exception))
        finally:
            os.environ["AGENTY_SESSION_TOKEN"] = TOKEN

    def test_busy_conversation_is_an_error(self):
        with self.assertRaises(host.HostError) as cm:
            host.start_turn("busy")
        self.assertIn("409", str(cm.exception))

    def test_conversations_are_trimmed(self):
        self.assertEqual(host.conversations(), [{"id": "c1", "title": "A", "running": False}])

    def test_host_down_is_a_clear_error(self):
        old = os.environ["AGENTY_HOST_URL"]
        os.environ["AGENTY_HOST_URL"] = "http://127.0.0.1:1"
        try:
            with self.assertRaises(host.HostError) as cm:
                host.start_turn("hi")
            self.assertIn("not reachable", str(cm.exception))
        finally:
            os.environ["AGENTY_HOST_URL"] = old

    def test_token_comes_from_a_file(self):
        del os.environ["AGENTY_SESSION_TOKEN"]
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".agenty_token"
            f.write_text(TOKEN + "\n")
            os.environ["AGENTY_TOKEN_FILE"] = str(f)
            try:
                self.assertEqual(host.session_token(), TOKEN)
                f.write_text("bad token!")
                self.assertNotEqual(host.session_token(), "bad token!")
            finally:
                del os.environ["AGENTY_TOKEN_FILE"]
                os.environ["AGENTY_SESSION_TOKEN"] = TOKEN

    def test_the_mcp_tools_return_json_and_never_raise(self):
        from src.tools import agenty_host as tools
        out = json.loads(asyncio.run(tools.agenty_turn("hi")))
        self.assertEqual(out["status"], "done")
        os.environ["AGENTY_HOST_URL"] = "http://127.0.0.1:1"
        try:
            self.assertIn("error", json.loads(asyncio.run(tools.agenty_turn("hi"))))
        finally:
            os.environ["AGENTY_HOST_URL"] = f"http://127.0.0.1:{self.srv.server_port}"

    def test_tools_are_registered(self):
        from src import mcp_server
        names = {getattr(f, "__name__", "") for f in mcp_server._TOOLS}
        for n in ("agenty_turn", "agenty_turn_status", "agenty_conversations",
                  "agenty_reply", "agenty_stop"):
            self.assertIn(n, names)


if __name__ == "__main__":
    unittest.main()
