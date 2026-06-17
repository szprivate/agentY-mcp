"""Compatibility shim — implementation moved to ``agenty_core.tools.shell``.

Kept so existing ``from src.tools.shell import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.tools import shell as _mod
_sys.modules[__name__] = _mod
