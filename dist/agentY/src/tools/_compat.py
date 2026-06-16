"""Compatibility shim: a no-op ``tool`` decorator.

The tool modules were originally written for the Strands Agents SDK, whose
``@tool`` decorator wrapped each function into an agent-callable object. Under
the MCP server the plain functions are registered with FastMCP centrally
(see ``src/mcp_server.py``), so this decorator only needs to return the function
unchanged. It accepts both the bare ``@tool`` form and the parametrised
``@tool(...)`` form for forward compatibility.
"""

from __future__ import annotations

from typing import Any, Callable


def tool(func: Callable | None = None, *_args: Any, **_kwargs: Any):
    """No-op replacement for ``strands.tool``.

    Returns the decorated function untouched so the module-level functions stay
    ordinary callables that FastMCP can introspect.
    """
    if func is not None and callable(func):
        return func

    def _wrap(f: Callable) -> Callable:
        return f

    return _wrap
