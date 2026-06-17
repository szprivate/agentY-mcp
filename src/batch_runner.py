"""Compatibility shim — implementation moved to ``agenty_core.batch_runner``.

Kept so existing ``from src.batch_runner import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core import batch_runner as _mod
_sys.modules[__name__] = _mod
