"""Keep the project venv in line with requirements.txt and agentY-core, on every start.

agentY-core's dependencies (OpenEXR, ...) reach this venv only through
``-e ../agentY-core`` in requirements.txt. When core adds one, nothing re-installs
it here and a tool fails late (an Atlas call after it was billed). Same remedy as
agentY's scripts/sync_deps.py: a fingerprint of the dependency files, stored in the
venv, plus an import check; the install runs when either says so.

Rules for an stdio MCP server: stdout belongs to the protocol, so everything here
goes to stderr; an unchanged environment costs one hash over two small files; a
failed install is logged and the server starts anyway.

Only the project's own ``.venv`` is managed. A packaged plugin/bundle (lib/ or uv's
cache) and any other interpreter are left alone. ``AGENTY_SKIP_DEP_SYNC=1`` opts out.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMP_NAME = ".agenty-deps"
INSTALL_TIMEOUT = 900
# Modules the server and the tool layer import; a miss means a re-install is due.
# agenty_core is left out: src/__init__ resolves it through the sibling checkout.
REQUIRED = ("mcp", "requests", "websockets", "dotenv", "PIL",
            "numpy", "OpenEXR", "jsonata", "scenedetect")


def _log(msg: str) -> None:
    print(f"[deps] {msg}", file=sys.stderr, flush=True)


def core_dir() -> Path:
    for name in ("agentY-core", "agenty_core"):
        if (ROOT.parent / name).is_dir():
            return ROOT.parent / name
    return ROOT.parent / "agentY-core"


def dep_files() -> tuple:
    return (ROOT / "requirements.txt", core_dir() / "pyproject.toml")


def fingerprint(files=None) -> str:
    """One hash over the dependency files; line endings normalised."""
    digest = hashlib.sha256()
    for path in (dep_files() if files is None else files):
        path = Path(path)
        digest.update(path.name.encode("utf-8"))
        try:
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        except OSError:
            digest.update(b"<absent>")
    return digest.hexdigest()


def stamp_path() -> Path:
    return Path(sys.prefix) / STAMP_NAME


def read_stamp():
    try:
        return stamp_path().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def write_stamp(value: str) -> None:
    try:
        stamp_path().write_text(value + "\n", encoding="utf-8")
    except OSError:
        pass  # unwritable venv: the check just runs again next start


def missing_required() -> list:
    missing = []
    for module in REQUIRED:
        try:
            if importlib.util.find_spec(module) is None:
                missing.append(module)
        except (ImportError, ValueError):
            missing.append(module)
    return missing


def reasons(stamp, current: str, missing: list) -> list:
    why = []
    if stamp is not None and stamp != current:
        why.append("requirements changed since this environment was last installed")
    if missing:
        why.append("missing: " + ", ".join(missing))
    return why


def install_command(python: str) -> list:
    """uv when present, pip otherwise; always naming this venv's interpreter."""
    if shutil.which("uv"):
        return ["uv", "pip", "install", "--python", python, "-r", "requirements.txt"]
    return [python, "-m", "pip", "install", "-r", "requirements.txt"]


def managed_venv() -> bool:
    """True only when running from this checkout's own .venv."""
    try:
        return ((ROOT / "requirements.txt").is_file() and not (ROOT / "lib").is_dir()
                and Path(sys.prefix).resolve() == (ROOT / ".venv").resolve())
    except OSError:
        return False


def sync() -> bool:
    """Install when needed. Returns True when an install ran and succeeded."""
    current = fingerprint()
    stamp = read_stamp()
    why = reasons(stamp, current, missing_required())
    if not why:
        if stamp != current:
            write_stamp(current)
        return False
    _log("installing from requirements.txt - " + "; ".join(why))
    command = install_command(sys.executable)
    try:
        # requirements.txt names the tool layer as `-e ../agentY-core`, relative to ROOT.
        proc = subprocess.run(command, cwd=str(ROOT), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=INSTALL_TIMEOUT)
        for line in proc.stdout.decode("utf-8", "replace").splitlines():
            _log(line)
        code = proc.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        _log(f"could not run {command[0]}: {exc}")
        code = 1
    if code != 0:
        _log(f"the install returned {code}; starting anyway, some tools may fail until it succeeds")
        return False
    write_stamp(current)
    importlib.invalidate_caches()
    return True


def ensure() -> None:
    """Called at server start. Never raises, never writes to stdout."""
    if os.environ.get("AGENTY_SKIP_DEP_SYNC") == "1" or not managed_venv():
        return
    try:
        sync()
    except Exception as exc:  # noqa: BLE001 - never the reason a start fails
        _log(f"dependency check failed: {exc}")
