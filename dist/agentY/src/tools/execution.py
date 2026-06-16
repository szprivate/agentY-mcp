"""Blocking workflow-execution tools for the MCP server.

These wrap the async streaming executor (``src/executor.py``) into single-call
MCP tools. Each tool submits the validated workflow(s) to ComfyUI, waits for
completion (polling over a WebSocket — no model tokens burned during the wait),
then returns a text summary **plus the output image(s)** — or sampled frames for
videos — as image content so the calling model can QA the result directly.

This replaces both the Strands ``signal_workflow_ready`` handoff and the old
Ollama Vision-QA pass: the model is multimodal and inspects the outputs itself.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PILImage
from mcp.server.fastmcp import Image as MCPImage

from src.tools._compat import tool
from src.tools.image_handling import _downsize
from src.executor import (
    execute_workflow as _stream_one,
    execute_workflows_batch as _stream_batch,
)

# Output file extensions treated as still images.
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
# Cap on how many images are returned to the model so a large batch can't blow
# up the response payload. Video frames count toward this cap too.
_MAX_RETURN_IMAGES = 8
_VIDEO_FRAME_SAMPLES = 3


def _image_block_from_path(path: Path) -> MCPImage | None:
    """Load a still image from disk, downsize to vision limits, and wrap it.

    Re-encodes via PIL to PNG/JPEG so any container (webp/bmp/gif) is accepted,
    then applies the shared ``_downsize`` to satisfy the 5 MB / 1568 px limits.
    Returns ``None`` on any failure (a missing/corrupt file is skipped, not fatal).
    """
    try:
        raw = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg"):
            img_fmt = "jpeg" if suffix in (".jpg", ".jpeg") else "png"
        else:
            # Normalise exotic formats to PNG bytes first.
            with PILImage.open(io.BytesIO(raw)) as im:
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                raw = buf.getvalue()
            img_fmt = "png"
        data, fmt = _downsize(raw, img_fmt)
        return MCPImage(data=data, format=fmt)
    except Exception:
        return None


def _image_blocks_for_outputs(paths: list[str]) -> list[MCPImage]:
    """Return image content blocks for output *paths* (stills + sampled video frames)."""
    from src.utils.video_frames import extract_frames, is_video

    blocks: list[MCPImage] = []
    for raw_path in paths:
        if len(blocks) >= _MAX_RETURN_IMAGES:
            break
        p = Path(raw_path)
        if not p.exists():
            continue
        if p.suffix.lower() in _IMAGE_SUFFIXES:
            block = _image_block_from_path(p)
            if block is not None:
                blocks.append(block)
        elif is_video(p):
            for frame in extract_frames(p, count=_VIDEO_FRAME_SAMPLES):
                if len(blocks) >= _MAX_RETURN_IMAGES:
                    break
                block = _image_block_from_path(frame)
                if block is not None:
                    blocks.append(block)
    return blocks


def _build_result(log: list[str], outputs: list[str]) -> list:
    """Assemble the tool return: a text summary followed by output image blocks."""
    blocks = _image_blocks_for_outputs(outputs)
    summary_lines = list(log)
    if outputs:
        summary_lines.append("")
        summary_lines.append("Output files (full-resolution originals on disk):")
        summary_lines.extend(f"- {p}" for p in outputs)
        if blocks:
            summary_lines.append("")
            summary_lines.append(
                "The image(s) below are downsized copies for inline viewing — use "
                "the paths above for the unresized originals."
            )
    else:
        summary_lines.append("⚠️ No output files were produced.")
    summary = "\n".join(summary_lines)
    return [summary, *blocks]


@tool
async def execute_workflow(workflow_path: str, brainbriefing_json: str = "") -> list:
    """Run a fully-assembled, validated workflow on ComfyUI and return its outputs.

    Call this as the final step once ``validate_workflow`` (or ``update_workflow``)
    reports the workflow is ready. It submits the workflow, waits for ComfyUI to
    finish, resolves every output file's on-disk path, and returns a status
    summary together with the generated image(s) (or sampled video frames) so you
    can immediately inspect the result and decide whether it satisfies the request.

    Args:
        workflow_path:      Path to the validated workflow JSON (as returned by
                            ``get_workflow_template`` / ``save_workflow`` and
                            patched via ``update_workflow``).
        brainbriefing_json: Optional brainbriefing JSON string. When provided, its
                            ``output_nodes[].output_path`` entries are used to
                            resolve where each output was saved.

    Returns:
        A text summary (status lines + output file paths) followed by the output
        image content for direct visual QA.
    """
    collected: list[str] = []
    log: list[str] = []
    async for line in _stream_one(
        workflow_path, brainbriefing_json, verbose=False, collected_paths=collected
    ):
        if isinstance(line, str):
            log.append(line)
    return _build_result(log, collected)


@tool
async def execute_workflows_batch(workflow_paths: list, brainbriefing_json: str = "") -> list:
    """Run several validated workflows (a batch) on ComfyUI and return their outputs.

    Use this for batch / variation runs — e.g. the per-variation workflow copies
    produced by ``duplicate_workflow``. All workflows are submitted up front, then
    polled in order, so ComfyUI can start working the queue immediately.

    Args:
        workflow_paths:     Ordered list of validated workflow JSON file paths.
        brainbriefing_json: Optional brainbriefing JSON string (for output paths).

    Returns:
        A text summary (per-iteration status + output file paths) followed by the
        output image content for direct visual QA.
    """
    paths = [str(p) for p in (workflow_paths or [])]
    collected: list[str] = []
    log: list[str] = []
    async for line in _stream_batch(
        paths, brainbriefing_json, verbose=False, collected_paths=collected
    ):
        if isinstance(line, str):
            log.append(line)
    return _build_result(log, collected)
