"""Compatibility shim — implementation moved to ``agenty_core.utils.progress_signal``.

Kept so existing ``from src.utils.progress_signal import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.utils import progress_signal as _mod
_sys.modules[__name__] = _mod
