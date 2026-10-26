"""A client for a RUNNING agentY host (the headless SSE host, default port 5000).

agentY is an application with its own orchestrator, skills and hooks. This module
lets another program hand it a message and get the finished turn back, instead of
driving the ComfyUI browser panel. It talks to the host's turn API
(``POST /agentY/turns``, ``GET /agentY/turns/<id>``), so the work is done by
agentY itself — not by the tool layer this repository also exposes.

Standard library only, so the command-line script works without installing
anything.

Where the host is and how to get in
-----------------------------------
* URL: ``AGENTY_HOST_URL`` (default ``http://127.0.0.1:5000``). The host refuses a
  request whose Host header names anything but an IP literal or ``localhost``.
* Token: the host keeps its session token in ``<agentY checkout>/.agenty_token``
  (owner-only, gitignored) and requires it in the ``X-AgentY-Token`` header. It is
  looked up in this order: ``AGENTY_SESSION_TOKEN``; the file named by
  ``AGENTY_TOKEN_FILE``; ``$AGENTY_HOME/.agenty_token``; ``../agentY/.agenty_token``
  beside this checkout. Anything that can read that file can already read ``.env``.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

TOKEN_HEADER = "X-AgentY-Token"
TOKEN_FILENAME = ".agenty_token"
DEFAULT_URL = "http://127.0.0.1:5000"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
# One long-poll slice. Below any proxy/idle limit, above the host's 5 s wake-up.
_SLICE_S = 45


class HostError(RuntimeError):
    """The host could not be reached, refused us, or refused the request."""


def host_url() -> str:
    return (os.environ.get("AGENTY_HOST_URL") or DEFAULT_URL).rstrip("/")


def _token_candidates() -> list[Path]:
    out: list[Path] = []
    named = (os.environ.get("AGENTY_TOKEN_FILE") or "").strip()
    if named:
        out.append(Path(named))
    home = (os.environ.get("AGENTY_HOME") or "").strip()
    if home:
        out.append(Path(home) / TOKEN_FILENAME)
    here = Path(__file__).resolve()
    out.append(here.parents[3] / "agentY" / TOKEN_FILENAME)   # sibling checkout
    return out


def session_token() -> str:
    """The host's session token, or "" when none can be found."""
    forced = (os.environ.get("AGENTY_SESSION_TOKEN") or "").strip()
    if forced:
        return forced
    for path in _token_candidates():
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if _TOKEN_RE.match(raw):
            return raw
    return ""


def request(method: str, path: str, body: dict | None = None, timeout: float = 30.0) -> dict:
    """One JSON call to the host. Raises :class:`HostError` with an actionable message."""
    url = host_url() + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    token = session_token()
    if token:
        headers[TOKEN_HEADER] = token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            detail = json.loads(raw).get("error") or raw
        except ValueError:
            detail = raw
        if exc.code == 403:
            detail = (f"{detail} (token {'found' if token else 'NOT found'}; set "
                      "AGENTY_SESSION_TOKEN or AGENTY_TOKEN_FILE, or AGENTY_HOME to the "
                      "agentY checkout)")
        raise HostError(f"agentY host answered {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise HostError(f"agentY host not reachable at {host_url()} ({exc}). Is it running "
                        "(run_agent.ps1)? If it listens elsewhere, set AGENTY_HOST_URL.") from None


def start_turn(message: str, conversation: str | None = None,
               attachments: list[str] | None = None, title: str | None = None,
               canvas: str | None = None) -> dict:
    body: dict = {"message": message}
    if canvas:
        body["canvas"] = canvas
    if conversation:
        body["conversation"] = conversation
    if title:
        body["title"] = title
    if attachments:
        body["attachments"] = [os.path.abspath(p) for p in attachments]
    return request("POST", "/agentY/turns", body)


def turn_status(turn_id: str, wait_s: float = 0) -> dict:
    wait_s = max(0.0, min(float(wait_s or 0), 120.0))
    return request("GET", f"/agentY/turns/{turn_id}" + (f"?wait={wait_s:g}" if wait_s else ""),
                   timeout=wait_s + 20)


def run_turn(message: str, conversation: str | None = None, wait: bool = True,
             timeout_s: float = 1800, attachments: list[str] | None = None,
             title: str | None = None, canvas: str | None = None) -> dict:
    """Start a turn; with *wait*, follow it until it ends, stops to ask something
    (``status == "waiting"``), or *timeout_s* passes (``timed_out``; the turn keeps
    running and can be read with :func:`turn_status`)."""
    started = start_turn(message, conversation, attachments, title, canvas)
    if not wait:
        return started
    turn_id = started["turn_id"]
    deadline = time.time() + max(1.0, float(timeout_s))
    flaky = 0
    while True:
        left = deadline - time.time()
        try:
            res = turn_status(turn_id, max(0.0, min(left, _SLICE_S)) if left > 0 else 0)
            flaky = 0
        except HostError as exc:
            # A restart of the host loses the turn; a blip does not. Allow a few.
            flaky += 1
            if flaky > 3 or "404" in str(exc):
                raise
            time.sleep(2)
            continue
        if res.get("status") != "running":
            return res
        if left <= 0:
            res["timed_out"] = True
            res["note"] = ("still running on the host; read it with agenty_turn_status(turn_id)")
            return res


def conversations(limit: int = 30) -> list[dict]:
    rows = request("GET", "/agentY/threads")
    if not isinstance(rows, list):
        rows = rows.get("threads", []) if isinstance(rows, dict) else []
    keep = ("id", "title", "running", "created_at", "updated_at", "message_count", "lead_id")
    out = [{k: r[k] for k in keep if k in r} for r in rows if isinstance(r, dict)]
    return out[: max(1, int(limit))]


def reply(request_id: str, text: str) -> dict:
    return request("POST", "/agentY/reply", {"request_id": request_id, "text": text})


def stop(turn_id: str = "", conversation: str = "") -> dict:
    body = {}
    if turn_id:
        body["request_id"] = turn_id
    if conversation:
        body["thread_id"] = conversation
    return request("POST", "/agentY/stop", body)
