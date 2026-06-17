"""Compatibility shim — implementation moved to ``agenty_core.tools.file_tools``.

Kept so existing ``from src.tools.file_tools import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.tools import file_tools as _mod
_sys.modules[__name__] = _mod
