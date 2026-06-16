"""
ComfyUI node-type → model folder mapping.

Used by download_hf_model to resolve where to store a downloaded model file
based on the ComfyUI node class that references it.

Usage
-----
    from src.utils.model_node_mapping import get_storage_path

    dest = get_storage_path("UNETLoader", "flux1-dev.safetensors", "/AI/ComfyUI")
    # → /AI/ComfyUI/models/unet/flux1-dev.safetensors
"""

import os

# ---------------------------------------------------------------------------
# Mapping: ComfyUI node class → relative folder under the ComfyUI root
# ---------------------------------------------------------------------------

NODE_TO_FOLDER: dict[str, str] = {
    # Checkpoints (SD1.5, SDXL, etc.)
    "CheckpointLoaderSimple": "models/checkpoints",
    "CheckpointLoader": "models/checkpoints",
    "unCLIPCheckpointLoader": "models/checkpoints",
    "CheckpointLoaderNF4": "models/checkpoints",

    # UNETs (Flux, Wan, modern diffusion models)
    "UNETLoader": "models/unet",
    "UnetLoaderGGUF": "models/unet",

    # LoRAs
    "LoraLoader": "models/loras",
    "LoraLoaderModelOnly": "models/loras",
    "LoRALoader": "models/loras",  # case variant

    # VAEs
    "VAELoader": "models/vae",

    # CLIP Text Encoders
    "CLIPLoader": "models/clip",
    "DualCLIPLoader": "models/clip",
    "TripleCLIPLoader": "models/clip",
    "CLIPVisionLoader": "models/clip_vision",

    # ControlNets
    "ControlNetLoader": "models/controlnet",
    "DiffControlNetLoader": "models/controlnet",
    "ControlNetLoaderAdvanced": "models/controlnet",

    # Upscale Models
    "UpscaleModelLoader": "models/upscale_models",
    "LatentUpscaleModelLoader": "models/latent_upscale_models",

    # GLIGEN (text-to-image guidance)
    "GLIGENLoader": "models/gligen",

    # Style Models
    "StyleModelLoader": "models/style_models",

    # Embeddings / Textual Inversion
    "Embedding": "models/embeddings",  # referenced in prompts, not a loader node

    # Hypernetworks (legacy)
    "HypernetworkLoader": "models/hypernetworks",

    # PhotoMaker (ID consistency)
    "PhotoMakerLoader": "models/photomaker",

    # IP-Adapter
    "IPAdapterModelLoader": "models/ipadapter",
    "IPAdapterUnifiedLoader": "models/ipadapter",

    # InstantID
    "InstantIDModelLoader": "models/instantid",

    # Segmentation / Detection
    "UltralyticsDetectorProvider": "models/ultralytics/bbox",
    "SAMModelLoader": "models/sams",  # Segment Anything

    # AnimateDiff
    "AnimateDiffLoader": "models/animatediff_models",
    "AnimateDiffMotionLoRA": "models/animatediff_motion_lora",

    # CogVideoX
    "CogVideoXModelLoader": "models/CogVideo/CogVideoX",

    # Mochi (video)
    "MochiModelLoader": "models/mochi",

    # LTX Video
    "LTXVModelLoader": "models/ltxv",
    "LTXAVTextEncoderLoader": "models/text_encoders",
    "LTXVAudioVAELoader": "models/checkpoints",

    # Model Patches
    "ModelPatchLoader": "models/model_patches",
}


# ---------------------------------------------------------------------------
# Mapping: ComfyUI node class → input parameter name(s) that hold the filename
# ---------------------------------------------------------------------------

NODE_TO_PARAM: dict[str, str | list[str]] = {
    "CheckpointLoaderSimple": "ckpt_name",
    "CheckpointLoader": "ckpt_name",
    "unCLIPCheckpointLoader": "ckpt_name",
    "CheckpointLoaderNF4": "ckpt_name",
    "UNETLoader": "unet_name",
    "UnetLoaderGGUF": "unet_name",
    "LoraLoader": "lora_name",
    "LoraLoaderModelOnly": "lora_name",
    "LoRALoader": "lora_name",
    "VAELoader": "vae_name",
    "CLIPLoader": "clip_name",
    "DualCLIPLoader": ["clip_name1", "clip_name2"],   # takes TWO files
    "TripleCLIPLoader": ["clip_name1", "clip_name2", "clip_name3"],
    "CLIPVisionLoader": "clip_name",
    "ControlNetLoader": "control_net_name",
    "DiffControlNetLoader": "control_net_name",
    "ControlNetLoaderAdvanced": "control_net_name",
    "UpscaleModelLoader": "model_name",
    "LatentUpscaleModelLoader": "model_name",
    "GLIGENLoader": "gligen_name",
    "StyleModelLoader": "style_model_name",
    "HypernetworkLoader": "hypernetwork_name",
    "PhotoMakerLoader": "photomaker_model_name",
    "IPAdapterModelLoader": "ipadapter_file",
    "IPAdapterUnifiedLoader": "model",
    "InstantIDModelLoader": "instantid_file",
    "UltralyticsDetectorProvider": "model_name",
    "SAMModelLoader": "model_name",
    "AnimateDiffLoader": "model_name",
    "AnimateDiffMotionLoRA": "lora_name",
    "CogVideoXModelLoader": "model",
    "MochiModelLoader": "model_name",
    "LTXVModelLoader": "model_name",
    "LTXAVTextEncoderLoader": "t5xxl_name",
    "LTXVAudioVAELoader": "vae_name",
    "ModelPatchLoader": "model_patch_name",
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_storage_path(node_class_type: str, filename: str, comfyui_base: str) -> str:
    """Return the absolute destination path for a model file.

    Args:
        node_class_type: ComfyUI node class name e.g. ``"UNETLoader"``.
        filename:        Model filename e.g. ``"flux1-dev.safetensors"``.
        comfyui_base:    Root directory of the ComfyUI installation,
                         e.g. ``"D:/AI/ComfyUI"``.  The ``models/`` subtree
                         lives directly underneath this directory.

    Returns:
        Absolute path string where the file should be stored.

    Raises:
        ValueError: If *node_class_type* is not in :data:`NODE_TO_FOLDER`.
    """
    folder = NODE_TO_FOLDER.get(node_class_type)
    if not folder:
        raise ValueError(
            f"Unknown node type: {node_class_type!r}. "
            f"Known types: {sorted(NODE_TO_FOLDER)}"
        )

    return os.path.join(comfyui_base, folder, filename)
