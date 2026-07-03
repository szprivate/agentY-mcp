"""Compatibility shim — implementation lives in
``agenty_core.tools.assembly_deterministic``.
"""
import sys as _sys
from agenty_core.tools import assembly_deterministic as _mod
_sys.modules[__name__] = _mod
