"""Compatibility shim — implementation moved to ``agenty_core.utils.secrets``.

Kept so existing ``from src.utils.secrets import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.utils import secrets as _mod
_sys.modules[__name__] = _mod
