"""
Utility functions for retrieving ComfyUI model lists.

These are plain (non-tool) helpers shared between:
  - src/tools/comfyui.py  (thin @tool wrappers for agent use)
  - scripts/refresh_models.py  (startup cache refresh)

Extensions recognised as actual model/weight files:
  ComfyUI core  → .ckpt .pt .pt2 .bin .pth .safetensors .pkl .sft
  GGUF quant    → .gguf
  ONNX graphs   → .onnx
Source: ComfyUI folder_paths.py `supported_pt_extensions` + common extras.
"""
from __future__ import annotations

from pathlib import Path

from src.utils.comfyui_client import get_client

MODEL_EXTENSIONS: frozenset[str] = frozenset({
    ".ckpt", ".pt", ".pt2", ".bin", ".pth",
    ".safetensors", ".pkl", ".sft",
    ".gguf",
    ".onnx",
})


def fetch_model_types() -> list[str]:
    """Return the list of model folder names reported by ComfyUI (/models)."""
    return get_client().get("/models")


def fetch_models_in_folder(folder: str) -> list[str]:
    """Return all entries in a ComfyUI model folder, unfiltered.

    Args:
        folder: Folder name e.g. 'checkpoints', 'loras', 'vae', 'unet'.
    """
    return get_client().get(f"/models/{folder}")


def fetch_available_models() -> dict[str, list[str] | dict]:
    """Return all installed model files grouped by folder type.

    Filters each folder to only real model/weight files (see MODULE_EXTENSIONS).
    The ``custom_nodes`` folder is excluded entirely.

    Folders that raise an error are included as ``{"error": "<message>"}``.

    Returns:
        {
            "checkpoints": ["FLUX1/flux1-dev-fp8.safetensors", ...],
            "loras": [...],
            ...
        }
    """
    client = get_client()
    folders: list[str] = client.get("/models")

    result: dict = {}
    for folder in folders:
        if folder == "custom_nodes":
            continue
        try:
            entries: list = client.get(f"/models/{folder}")
            result[folder] = [
                e for e in entries
                if Path(e).suffix.lower() in MODEL_EXTENSIONS
            ]
        except Exception as exc:
            result[folder] = {"error": str(exc)}

    return result
