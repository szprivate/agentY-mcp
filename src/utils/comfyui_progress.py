"""Compatibility shim — implementation moved to ``agenty_core.utils.comfyui_progress``.

Kept so existing ``from src.utils.comfyui_progress import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.utils import comfyui_progress as _mod
_sys.modules[__name__] = _mod
