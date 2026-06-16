"""
progress_signal – Thread-safe buffer for mid-tool progress lines.

Sync tools (e.g. download_hf_model) push formatted progress lines here
via ``push()``.  The async pipeline drains them via ``drain()`` and yields
each line as a ``{"data": "..."}`` event so Chainlit can display them.

Usage from a tool:
    from src.utils.progress_signal import push as push_progress
    push_progress("⬇️ [████░░░░░░] 45% …")

Usage from the pipeline:
    from src.utils.progress_signal import drain as drain_progress
    for line in drain_progress():
        yield {"data": line}
"""

from __future__ import annotations

import threading
from collections import deque

# Bounded so a long-running MCP server (whose consumer no longer drains this
# buffer) cannot accumulate progress lines without limit.
_lock: threading.Lock = threading.Lock()
_lines: deque[str] = deque(maxlen=200)


def push(line: str) -> None:
    """Append a progress line to the buffer (thread-safe)."""
    with _lock:
        _lines.append(line)


def drain() -> list[str]:
    """Atomically read and clear all buffered lines.

    Returns an empty list when no progress has been pushed since the last drain.
    """
    with _lock:
        if not _lines:
            return []
        out = list(_lines)
        _lines.clear()
        return out
