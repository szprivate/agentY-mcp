"""Compatibility shim — implementation moved to ``agenty_core.tools.huggingface``.

Kept so existing ``from src.tools.huggingface import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.tools import huggingface as _mod
_sys.modules[__name__] = _mod
