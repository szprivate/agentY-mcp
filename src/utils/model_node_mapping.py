"""Compatibility shim — implementation moved to ``agenty_core.utils.model_node_mapping``.

Kept so existing ``from src.utils.model_node_mapping import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.utils import model_node_mapping as _mod
_sys.modules[__name__] = _mod
