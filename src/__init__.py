# agentY — ComfyUI workflow toolkit, exposed as an MCP server (see src/mcp_server.py).
#
# Packaged-bundle bootstrap: in a .mcpb bundle or a Claude plugin the Python
# dependencies are vendored under <root>/lib. Hosts are *supposed* to put that on
# PYTHONPATH (the manifest / .mcp.json sets it), but some hosts don't apply the
# env block — Claude Code, for instance, expands ${CLAUDE_PLUGIN_ROOT} in
# `command`/`cwd` but not inside `env` values, so PYTHONPATH never reaches the
# process and `import mcp` fails ("Failed to connect"). So we bootstrap <root>/lib
# ourselves here, before any third-party import, making the server self-contained
# regardless of how the host handles env. No-op when running from source (no lib/).
#
# pywin32 (required by the mcp SDK on Windows) additionally needs its loader
# modules (lib/win32, lib/win32/lib) on sys.path and its DLLs (lib/pywin32_system32)
# on the DLL search path — its .pth file isn't processed outside site-packages.

import os as _os
import sys as _sys
from pathlib import Path as _Path


def _bootstrap_vendored_lib() -> None:
    lib = _Path(__file__).resolve().parent.parent / "lib"
    if not lib.is_dir():
        return  # running from source, not a packaged bundle/plugin

    # Put the vendored deps (and the bundle root) on sys.path so imports resolve
    # without relying on the host setting PYTHONPATH.
    for entry in (str(lib.parent), str(lib)):
        if entry not in _sys.path:
            _sys.path.insert(0, entry)

    # Windows: register pywin32's vendored loader dirs + DLL directory.
    if _sys.platform == "win32":
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


_bootstrap_vendored_lib()
