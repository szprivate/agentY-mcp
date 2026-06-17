"""Compatibility shim — implementation moved to ``agenty_core.utils.video_frames``.

Kept so existing ``from src.utils.video_frames import ...`` imports
keep working. The real code lives in the shared **agenty_core** package.
"""
import sys as _sys
from agenty_core.utils import video_frames as _mod
_sys.modules[__name__] = _mod
