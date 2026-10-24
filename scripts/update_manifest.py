"""Keep the package manifests of agentY-mcp true: versions and the tool list.

* ``manifest.json`` (the .mcpb bundle for Claude Desktop): ``version`` and ``tools``
  (every tool the server offers, with the start of its docstring);
* ``.claude-plugin/plugin.json`` and the entry in ``.claude-plugin/marketplace.json``:
  ``version``.

Run from this repo's root with its own interpreter. agentY's release script calls it
(``scripts/make_release.py``); the versions are the release version.

    .venv/Scripts/python.exe scripts/update_manifest.py --version 1.5.0
    .venv/Scripts/python.exe scripts/update_manifest.py            # refresh the tool list only
    .venv/Scripts/python.exe scripts/update_manifest.py --check [--version 1.5.0]   # exit 1 if a file would change
    .venv/Scripts/python.exe scripts/update_manifest.py --validate # also `claude plugin validate .`, when claude is on PATH
"""
from __future__ import annotations

import inspect
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FILES = {
    "mcpb": ROOT / "manifest.json",
    "plugin": ROOT / ".claude-plugin" / "plugin.json",
    "marketplace": ROOT / ".claude-plugin" / "marketplace.json",
}


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _dump(d: dict, mcpb: bool) -> str:
    # manifest.json has always been written with escaped non-ASCII; keep the files' own style.
    return json.dumps(d, indent=2, ensure_ascii=mcpb) + "\n"


def tool_list() -> list:
    from src import mcp_server
    out = []
    for fn in sorted(mcp_server._TOOLS, key=lambda f: f.__name__):
        para = " ".join((inspect.getdoc(fn) or "").strip().split(chr(10) * 2)[0].split())
        if len(para) > 120:
            para = para[:120].rsplit(" ", 1)[0] + " ..."
        out.append({"name": fn.__name__, "description": para})
    return out


def wanted(version: str | None, tools: list | None) -> dict:
    """{key: (path, new_text)} for the files as they should be."""
    out = {}
    mcpb = _read(FILES["mcpb"])
    if version:
        mcpb["version"] = version
    if tools is not None:
        mcpb["tools"] = tools
    out["mcpb"] = (FILES["mcpb"], _dump(mcpb, True))
    plugin = _read(FILES["plugin"])
    if version:
        plugin["version"] = version
    out["plugin"] = (FILES["plugin"], _dump(plugin, False))
    mk = _read(FILES["marketplace"])
    for entry in mk["plugins"]:
        if entry.get("name") == plugin["name"] and version:
            entry["version"] = version
    out["marketplace"] = (FILES["marketplace"], _dump(mk, False))
    return out


def stale(version: str | None, tools: list | None = None) -> list:
    """Names of the files that differ from what they should be."""
    tools = tool_list() if tools is None else tools
    return [p.name for p, text in wanted(version, tools).values()
            if p.read_text(encoding="utf-8-sig").replace("\r\n", "\n") != text]


def validate_plugin() -> tuple:
    """(ok, message). Skipped (ok) when the claude CLI is not on PATH."""
    claude = shutil.which("claude")
    if not claude:
        return True, "claude CLI not on PATH - plugin validation skipped"
    done = subprocess.run([claude, "plugin", "validate", str(ROOT)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    lines = ((done.stdout or "") + (done.stderr or "")).strip().splitlines()
    return done.returncode == 0, (lines[-1] if lines else "")


def main(argv: list) -> int:
    sys.stdout.reconfigure(errors="replace")
    version = None
    for i, a in enumerate(argv):
        if a == "--version" and i + 1 < len(argv):
            version = argv[i + 1]
        elif a.startswith("--version="):
            version = a.split("=", 1)[1]
    if version is not None and not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"'{version}' is not a version like 1.2.0")
        return 2
    if "--check" in argv:
        off = stale(version)
        print("Manifests are current." if not off else "Out of date: " + ", ".join(off)
              + "\nRun: .venv/Scripts/python.exe scripts/update_manifest.py" + (f" --version {version}" if version else ""))
        rc = 1 if off else 0
    else:
        for p, text in wanted(version, tool_list()).values():
            if p.read_text(encoding="utf-8-sig").replace("\r\n", "\n") != text:
                p.write_text(text, encoding="utf-8", newline="\n")
                print(f"updated {p.relative_to(ROOT)}")
        rc = 0
    if "--validate" in argv:
        ok, msg = validate_plugin()
        print(("plugin valid: " if ok else "PLUGIN INVALID: ") + msg)
        rc = rc or (0 if ok else 1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
