"""Talk to a running agentY host from an MCP client.

These tools hand a request to agentY ITSELF — its orchestrator, skills and hooks —
rather than to the tool layer this server also exposes. Use them when the job is
"do this the way agentY does it" (build and run a workflow, work the user's canvas,
follow a hook pipeline) and a top-level agent would otherwise have to drive the
ComfyUI browser panel. Turns also show live in the panel when it is open.

All of them need agentY's host running (default http://127.0.0.1:5000); see
``src/utils/agenty_host_client.py`` for how the URL and session token are found.
"""
from __future__ import annotations

import asyncio
import json

from src.utils import agenty_host_client as host


def _out(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _err(exc: Exception) -> str:
    return _out({"error": str(exc)})


async def agenty_turn(message: str, conversation: str | None = None, wait: bool = True,
                      timeout_s: int = 1800, attachments: list[str] | None = None,
                      title: str | None = None) -> str:
    """Send a message to the RUNNING agentY host and return what agentY did.

    agentY runs the turn exactly as if the user typed it in its ComfyUI panel
    (same orchestrator, skills and hooks) and, if that panel is open on the
    conversation, shows it live.

    Args:
        message: What to ask agentY, in plain words. Slash commands are not turns.
        conversation: A conversation id from an earlier result or agenty_conversations
            to continue it (agentY remembers it). Omit to start a new conversation.
            Different conversations run in parallel; one conversation runs one turn
            at a time (a second send is refused while it is busy).
        wait: True (default) follows the turn and returns the finished result.
            False returns {turn_id, conversation} at once; read it later with
            agenty_turn_status.
        timeout_s: How long to wait before giving up WAITING (the turn keeps running
            on the host; the result then has timed_out=true).
        attachments: Absolute paths of local images/videos to give the turn as inputs.
        title: Name for a new conversation.

    Returns JSON: status (done | error | waiting | running), reply (agentY's final
    text), tool_calls [{name, agent, status, input, result}], files [{path, kind,
    role}] it produced, canvas [{op, node_id, ...}] edits it made to the user's
    canvas, waiting {kind, prompt, request_id} when it stopped on a question or an
    open review (answer with agenty_reply, or send another message to the same
    conversation), usage {input, output, cost, calls}, turn_id, conversation.
    """
    try:
        res = await asyncio.to_thread(host.run_turn, message, conversation, wait,
                                      timeout_s, attachments, title)
        return _out(res)
    except host.HostError as exc:
        return _err(exc)


async def agenty_turn_status(turn_id: str, wait_s: int = 0) -> str:
    """The current state of a turn started with agenty_turn (same result shape).

    Args:
        turn_id: From agenty_turn.
        wait_s: Hold up to this many seconds (max 120) for the turn to end or to
            stop on a question before answering. 0 answers immediately.

    Finished turns are remembered for the last 100 turns, until the host restarts.
    """
    try:
        return _out(await asyncio.to_thread(host.turn_status, turn_id, wait_s))
    except host.HostError as exc:
        return _err(exc)


async def agenty_conversations(limit: int = 30) -> str:
    """List agentY's conversations (id, title, running) so one can be continued by
    passing its id as `conversation` to agenty_turn. Several can run in parallel."""
    try:
        return _out(await asyncio.to_thread(host.conversations, limit))
    except host.HostError as exc:
        return _err(exc)


async def agenty_reply(request_id: str, text: str) -> str:
    """Answer a question a running turn is waiting on (a result with
    status=waiting and waiting.request_id): "yes", "no", or a revision note."""
    try:
        return _out(await asyncio.to_thread(host.reply, request_id, text))
    except host.HostError as exc:
        return _err(exc)


async def agenty_stop(turn_id: str = "", conversation: str = "") -> str:
    """Stop a running agentY turn (by turn_id, or every turn of a conversation) and
    interrupt what it queued in ComfyUI."""
    try:
        return _out(await asyncio.to_thread(host.stop, turn_id, conversation))
    except host.HostError as exc:
        return _err(exc)
