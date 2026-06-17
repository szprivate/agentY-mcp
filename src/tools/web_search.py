"""Compatibility shim — implementation moved to ``agenty_core.tools.web_search``.

Kept so existing ``from src.tools.web_search import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.tools import web_search as _mod
_sys.modules[__name__] = _mod
