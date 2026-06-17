"""Compatibility shim — implementation moved to ``agenty_core.tools.workflow_registry``.

Kept so existing ``from src.tools.workflow_registry import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.tools import workflow_registry as _mod
_sys.modules[__name__] = _mod
