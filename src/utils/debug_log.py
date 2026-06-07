"""Toggleable debug tracing to pinpoint hangs and stalls.

Tracing is ON when **either**:

* the env var ``AGENTY_DEBUG`` is truthy (``1`` / ``true`` / ``yes`` / ``on``) —
  set it before launch, e.g. ``.\\run_agent.ps1 -Debug``; **or**
* the sentinel file ``.logs/agenty_debug.on`` exists — create it to enable
  tracing on an **already-running** process (no restart, no env var), as long
  as that process already loaded this instrumented build::

      New-Item .logs/agenty_debug.on      # enable
      Remove-Item .logs/agenty_debug.on   # disable

The enabled state is evaluated **dynamically on every call**, so the sentinel
toggles live.  When enabled, :func:`trace` writes a timestamped line — with the
elapsed time since the previous trace and the current thread name — to stderr
and to ``.logs/debug.log``.  Place ``trace()`` calls on both sides of every
await that could block; after a hang the **last** line written identifies
exactly where execution stopped.

The whole module is a near-zero-cost no-op when tracing is off.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / ".logs"
_LOG_PATH = _LOG_DIR / "debug.log"
_SENTINEL = _LOG_DIR / "agenty_debug.on"
_lock = threading.Lock()
_last_t = time.monotonic()


def debug_enabled() -> bool:
    """Return ``True`` when tracing is currently enabled (env var or sentinel)."""
    if os.environ.get("AGENTY_DEBUG", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    try:
        return _SENTINEL.exists()
    except Exception:
        return False


def trace(msg: str) -> None:
    """Write a timestamped trace line (a no-op unless tracing is enabled)."""
    if not debug_enabled():
        return
    global _last_t
    now = time.monotonic()
    with _lock:
        delta = now - _last_t
        _last_t = now
    line = (
        f"{time.strftime('%H:%M:%S')} (+{delta:6.2f}s) "
        f"[{threading.current_thread().name}] {msg}"
    )
    print(f"🔎 TRACE {line}", file=sys.stderr, flush=True)
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
