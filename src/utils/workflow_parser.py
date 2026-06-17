"""Compatibility shim — implementation moved to ``agenty_core.utils.workflow_parser``.

Kept so existing ``from src.utils.workflow_parser import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.utils import workflow_parser as _mod
_sys.modules[__name__] = _mod
