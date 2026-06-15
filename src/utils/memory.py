"""
agentY – Local file-based long-term memory.

A dependency-free replacement for the previous FAISS + mem0 + Ollama-embeddings
stack (removed with the MCP migration). Memories are stored as plain JSON records
on disk and retrieved with keyword/substring scoring — no embeddings, no network.

Storage
-------
  ./memory/agenty_memory.json   →  {"records": [{id, session_id, content, ts}, ...]}

Public API (unchanged, consumed by src/tools/memory_tools.py)
------------------------------------------------------------
>>> from src.utils.memory import memory_search, memory_add, format_memories
>>> memory_add("User prefers 1024x1024 for portrait shots.", session_id="abc")
>>> hits = memory_search("portrait resolution", session_id="abc")
>>> print(format_memories(hits))

Disable entirely with the env var ``MEMORY_ENABLED=false``.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MEMORY_DIR = _PROJECT_ROOT / "memory"
_MEMORY_FILE = _MEMORY_DIR / "agenty_memory.json"

_lock = threading.Lock()

# Words ignored when scoring a query so common filler doesn't inflate matches.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "is",
    "are", "was", "were", "be", "user", "users", "please", "want", "wants",
    "remember", "memory", "note", "that", "this", "my", "i", "it",
}


# ---------------------------------------------------------------------------
# Enable / disable
# ---------------------------------------------------------------------------

def _is_enabled() -> bool:
    """Return False only when MEMORY_ENABLED is explicitly falsy."""
    env = os.environ.get("MEMORY_ENABLED", "").strip().lower()
    return env not in ("0", "false", "no", "off")


# ---------------------------------------------------------------------------
# Disk I/O (thread-safe, best-effort atomic)
# ---------------------------------------------------------------------------

def _load() -> list[dict[str, Any]]:
    if not _MEMORY_FILE.exists():
        return []
    try:
        data = json.loads(_MEMORY_FILE.read_text(encoding="utf-8"))
        records = data.get("records", []) if isinstance(data, dict) else []
        return [r for r in records if isinstance(r, dict) and r.get("content")]
    except Exception:
        return []


def _save(records: list[dict[str, Any]]) -> None:
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _MEMORY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"records": records}, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_MEMORY_FILE)


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def memory_add(content: str, session_id: str = "default") -> None:
    """Persist a single fact. Exact duplicates (same content) are ignored."""
    content = (content or "").strip()
    if not content or not _is_enabled():
        return
    with _lock:
        records = _load()
        if any(r.get("content", "").strip() == content for r in records):
            return
        records.append(
            {
                "id": uuid.uuid4().hex,
                "session_id": session_id,
                "content": content,
                "ts": time.time(),
            }
        )
        _save(records)


def memory_search(query: str, session_id: str = "default", limit: int = 5) -> list[dict[str, Any]]:
    """Return up to *limit* records most relevant to *query*.

    Scoring is keyword overlap (one point per distinct query token found in the
    record) plus a substring bonus, tie-broken by recency. An empty query
    returns the most recent records. Search spans all sessions — this is a
    single-user local store.
    """
    if not _is_enabled():
        return []
    with _lock:
        records = _load()
    if not records:
        return []

    q_tokens = set(_tokenize(query))
    if not q_tokens:
        # No meaningful query terms — return most recent.
        return sorted(records, key=lambda r: r.get("ts", 0), reverse=True)[:limit]

    q_lower = query.lower().strip()
    scored: list[tuple[float, float, dict]] = []
    for r in records:
        content = r.get("content", "")
        c_tokens = set(_tokenize(content))
        overlap = len(q_tokens & c_tokens)
        if overlap == 0 and q_lower not in content.lower():
            continue
        score = float(overlap)
        if q_lower and q_lower in content.lower():
            score += 2.0
        scored.append((score, r.get("ts", 0.0), r))

    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [r for _score, _ts, r in scored[:limit]]


def format_memories(results: list[dict[str, Any]]) -> str:
    """Render search results as a markdown bullet list, or "" when empty."""
    if not results:
        return ""
    lines = ["Relevant long-term memories:"]
    for r in results:
        content = r.get("content") or r.get("memory") or ""
        if content:
            lines.append(f"- {content}")
    return "\n".join(lines) if len(lines) > 1 else ""
