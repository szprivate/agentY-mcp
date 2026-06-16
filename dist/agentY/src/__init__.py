# agentY — ComfyUI workflow toolkit, exposed as an MCP server (see src/mcp_server.py).
#
# Packaged-bundle bootstrap: in a .mcpb bundle the Python dependencies are vendored
# under <bundle>/lib. pywin32 (required by the mcp SDK on Windows) ships its loader
# modules in lib/win32/lib and its DLLs in lib/pywin32_system32 — directories that its
# .pth file would normally register, but .pth files outside site-packages are not
# processed. Register them here, before mcp is imported. No-op when running from
# source (no lib/ dir) or on non-Windows.

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _bootstrap_vendored_pywin32() -> None:
    if _sys.platform != "win32":
        return
    lib = _Path(__file__).resolve().parent.parent / "lib"
    if not lib.is_dir():
        return  # running from source, not a packaged bundle
    for sub in ("win32", "win32/lib", "pythonwin"):
        p = lib / sub
        if p.is_dir() and str(p) not in _sys.path:
            _sys.path.insert(0, str(p))
    dll_dir = lib / "pywin32_system32"
    if dll_dir.is_dir():
        try:
            _os.add_dll_directory(str(dll_dir))
        except (OSError, AttributeError):
            pass
        _os.environ["PATH"] = str(dll_dir) + _os.pathsep + _os.environ.get("PATH", "")


_bootstrap_vendored_pywin32()
