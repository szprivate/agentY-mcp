"""Compatibility shim — implementation moved to ``agenty_core.tools.comfyui``.

Kept so existing ``from src.tools.comfyui import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.tools import comfyui as _mod
_sys.modules[__name__] = _mod
