"""
comfyui_progress – WebSocket-based live progress streamer for ComfyUI jobs.

Connects to ``ws://<comfyui>/ws?clientId=<uuid>`` and yields one-line status
updates (queue position, per-node progress bars, errors) as ComfyUI emits
events.  This is the sole completion path for ComfyUI jobs in agentY.

Yields:
    str  — human-readable status line (progress bar, node-start, etc.)
    dict — terminal result, exactly one of:
              {"history": <stripped_history_dict>}     on success
              {"error": str, "details"?: dict}         on error / timeout

The caller treats any dict yield as the end of the stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator
from urllib.parse import urlparse

logger = logging.getLogger("agentY.comfyui_progress")


def _bar(value: int, max_value: int, width: int = 20) -> str:
    if max_value <= 0:
        return ""
    pct = int(value / max_value * 100)
    filled = int(width * value / max_value)
    return f"[{'█' * filled}{'░' * (width - filled)}] {value}/{max_value} ({pct}%)"


def _has_outputs(entry) -> bool:
    """True if a /history entry has at least one saved output file."""
    if not isinstance(entry, dict):
        return False
    for node_out in (entry.get("outputs") or {}).values():
        if isinstance(node_out, dict) and any(
            node_out.get(k) for k in ("images", "gifs", "videos", "audio")
        ):
            return True
    return False


def _check_history(client, prompt_id: str):
    """Inline check of /history/{prompt_id}.  Returns terminal dict or None.

    A ``completed`` status is only treated as terminal once the prompt's output
    files have actually been written into ``/history`` — ComfyUI marks the job
    completed a moment before the outputs land, so returning early here would
    yield a history with empty ``outputs`` ("no output files found").  Returning
    None keeps the caller polling until the outputs appear.
    """
    from src.tools.comfyui import _strip_history

    try:
        raw = client.get(f"/history/{prompt_id}")
    except Exception as exc:
        logger.debug("history check failed: %s", exc)
        return None
    if not isinstance(raw, dict) or prompt_id not in raw:
        return None
    entry = raw[prompt_id]
    status_info = entry.get("status", {})
    if status_info.get("status_str") == "error":
        return {"error": "ComfyUI job failed", "details": _strip_history(raw)}
    if status_info.get("completed") and _has_outputs(entry):
        return {"history": _strip_history(raw)}
    return None


async def _fetch_history_with_outputs(client, prompt_id: str, *, attempts: int = 10, delay: float = 0.4):
    """Fetch /history for a finished prompt, retrying until its outputs appear.

    ComfyUI emits ``execution_success`` a beat before the prompt's output files
    are written into ``/history``; a single immediate fetch then returns an entry
    with empty ``outputs`` — the intermittent "no output files found" bug.  Retry
    a handful of times (cheap, no LLM tokens) until outputs are present, then
    return the stripped history.  Falls back to whatever was last fetched after
    the final attempt so a genuinely output-less workflow still terminates.
    """
    from src.tools.comfyui import _strip_history

    raw = None
    for attempt in range(1, attempts + 1):
        try:
            raw = client.get(f"/history/{prompt_id}")
        except Exception as exc:
            logger.debug("history fetch failed (attempt %d/%d): %s", attempt, attempts, exc)
            raw = None
        if isinstance(raw, dict) and _has_outputs(raw.get(prompt_id, {})):
            if attempt > 1:
                logger.info(
                    "executor: outputs appeared in /history after %d attempt(s)", attempt
                )
            return _strip_history(raw)
        if attempt < attempts:
            await asyncio.sleep(delay)
    logger.warning(
        "executor: /history for %s still has no outputs after %d attempts (%.1fs)",
        prompt_id, attempts, attempts * delay,
    )
    return _strip_history(raw) if isinstance(raw, dict) else {}


async def stream_comfyui_job(
    prompt_id: str,
    client_id: str,
    *,
    timeout: float = 30 * 60,
    node_titles: dict[str, str] | None = None,
) -> AsyncGenerator:
    """Stream live progress for *prompt_id* via the ComfyUI WebSocket.

    Args:
        prompt_id:   Returned by POST /prompt.
        client_id:   The same client_id passed to /prompt; used to subscribe.
        timeout:     Hard cap on total wait time (seconds).
        node_titles: Optional mapping of node_id -> display name, used to
                     annotate progress messages with human-readable names.

    Yields:
        Progress strings, then a single terminal dict.
    """
    import websockets

    from src.utils.comfyui_client import get_client

    client = get_client()
    parsed = urlparse(client.base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{parsed.netloc}/ws?clientId={client_id}"

    headers: list[tuple[str, str]] = []
    if client.api_key:
        headers.append(("Authorization", f"Bearer {client.api_key}"))

    # If the job already completed before we got here (common in batch flows),
    # short-circuit without opening a socket.
    pre = _check_history(client, prompt_id)
    if pre is not None:
        yield pre
        return

    last_progress_pct: int = -1
    last_emit_loop_t: float = 0.0
    elapsed: float = 0.0
    RECV_TIMEOUT = 5.0  # seconds — also drives periodic history fallback check

    try:
        connect_kwargs: dict = {"max_size": None}
        if headers:
            # websockets >= 12 uses additional_headers
            connect_kwargs["additional_headers"] = headers

        async with websockets.connect(ws_url, **connect_kwargs) as ws:
            while elapsed < timeout:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
                except asyncio.TimeoutError:
                    # No event for RECV_TIMEOUT — re-check history in case we
                    # missed the completion event (e.g. server restart, or the
                    # prompt finished between our pre-check and ws.connect).
                    elapsed += RECV_TIMEOUT
                    fallback = _check_history(client, prompt_id)
                    if fallback is not None:
                        yield fallback
                        return
                    continue

                if isinstance(raw, (bytes, bytearray)):
                    # Binary preview frames — not used for progress.
                    continue

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                data = msg.get("data", {}) or {}
                msg_prompt_id = data.get("prompt_id")

                # Filter to our prompt where the message carries one.
                if msg_prompt_id and msg_prompt_id != prompt_id:
                    continue

                if msg_type == "status":
                    qrem = (
                        data.get("status", {})
                        .get("exec_info", {})
                        .get("queue_remaining")
                    )
                    if qrem is not None and qrem > 0:
                        yield f"⏳ Queue: {qrem} job(s) ahead"

                elif msg_type == "execution_start":
                    yield "▶ Execution started"
                    last_progress_pct = -1

                elif msg_type == "execution_cached":
                    cached = data.get("nodes", []) or []
                    if cached:
                        yield f"💾 {len(cached)} node(s) served from cache"

                elif msg_type == "executing":
                    node = data.get("node")
                    if node is None:
                        # null node = prompt finished (older protocol); confirm via history
                        fallback = _check_history(client, prompt_id)
                        if fallback is not None:
                            yield fallback
                            return
                    else:
                        last_progress_pct = -1
                        _title = node_titles.get(str(node), "") if node_titles else ""
                        _node_label = f" · {_title}" if _title else ""
                        yield f"🎨 Running node {node}{_node_label}"

                elif msg_type == "progress":
                    value = int(data.get("value", 0) or 0)
                    max_v = int(data.get("max", 0) or 0)
                    node = data.get("node")
                    if max_v > 0:
                        pct = int(value / max_v * 100)
                        loop_t = asyncio.get_event_loop().time()
                        # Throttle: emit on first/last step, ≥10% jump, or ≥1s elapsed.
                        is_endpoint = value <= 1 or value >= max_v
                        big_jump = pct - last_progress_pct >= 10
                        time_due = loop_t - last_emit_loop_t >= 1.0
                        if is_endpoint or big_jump or time_due:
                            if node:
                                _title = node_titles.get(str(node), "") if node_titles else ""
                                node_label = f" — node {node}" + (f" · {_title}" if _title else "")
                            else:
                                node_label = ""
                            yield f"🎨 {_bar(value, max_v)}{node_label}"
                            last_progress_pct = pct
                            last_emit_loop_t = loop_t

                elif msg_type == "execution_success":
                    # Outputs can lag this event by a moment — retry /history
                    # until they appear instead of fetching once.
                    yield {"history": await _fetch_history_with_outputs(client, prompt_id)}
                    return

                elif msg_type == "execution_error":
                    err_msg = data.get("exception_message", "Unknown error")
                    node_type = data.get("node_type", "?")
                    node_id = data.get("node_id", "?")
                    yield f"❌ Error in {node_type} (node {node_id}): {err_msg}"
                    yield {
                        "error": "ComfyUI execution failed",
                        "details": {
                            "node_id": node_id,
                            "node_type": node_type,
                            "exception_type": data.get("exception_type", ""),
                            "exception_message": err_msg,
                            "traceback": data.get("traceback", []),
                        },
                    }
                    return

                elif msg_type == "execution_interrupted":
                    yield "🛑 Execution interrupted"
                    yield {"error": "Execution interrupted"}
                    return

            # Hard timeout
            yield {"error": f"WebSocket timeout after {timeout:.0f}s"}
            return

    except Exception as exc:
        logger.error("comfyui_progress: WebSocket failed for prompt_id=%s: %s", prompt_id, exc)
        yield {"error": f"WebSocket connection failed: {exc}"}
