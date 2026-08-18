"""
Image handling tools – upload, download, resolution, and visual analysis.

Consolidates all image-related @tool functions:
  • upload_image: push images to ComfyUI's input folder
  • view_image: download images from ComfyUI's output
  • get_image_resolution: read local image dimensions
  • analyze_image: forward an image to the model for visual inspection
"""

import io
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional

import requests
from PIL import Image
from mcp.server.fastmcp import Image as MCPImage

from src.tools._compat import tool
from src.utils.comfyui_client import get_client


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

# ── moved to agenty_core ─────────────────────────────────────────────────────
# The byte wrangling and the web fetch were maintained here AND in agentY at
# 98-100% identical; they now live in the shared layer, re-exported under the
# names this repo already imports (src/tools/execution.py takes _downsize).
#
# `download_image` is wrapped rather than re-exported for one reason: this host
# defaults its subfolder to "agent/references" and agentY defaults to the input
# root, because LoadImage on some ComfyUI builds cannot read input
# subdirectories. Preserving each host's own default keeps this a move and not a
# behaviour change — the two are worth reconciling, but not silently and not here.
from agenty_core.tools.image_io import (  # noqa: F401
    download_image as _core_download_image,
    stage_image as _stage_image,
    upload_file_to_url,
)
from agenty_core.utils.image_bytes import (  # noqa: F401
    MAX_IMAGE_BYTES as _MAX_IMAGE_BYTES,
    OPTIMAL_LONG_EDGE as _OPTIMAL_LONG_EDGE,
    detect_format as _detect_format,
    downsize as _downsize,
)


@tool
def download_image(image_url: str, subfolder: str = "agent/references",
                   downsize: bool = True) -> str:
    """Download a web image straight into ComfyUI's input folder so a workflow can load it.

    Use this right after ``web_search_images`` to fetch a reference image you
    found (pass the result's ``image_url``). The image is uploaded into ComfyUI's
    input directory under ``agent/references`` and can then be referenced directly
    by a ``LoadImage`` node using the returned ``name`` and ``subfolder`` — no
    separate ``upload_image`` call is needed.

    Args:
        image_url: Direct http/https URL of the image (the ``image_url`` field
                   returned by ``web_search_images``).
        subfolder: Input-dir subfolder to store the image in. Defaults to
                   ``agent/references``.
        downsize:  When True (default), oversized images are downscaled to the
                   5 MB / 1568 px limits so they stay usable everywhere. Set False
                   to keep the original full-resolution file.

    Returns:
        JSON ``{"name", "subfolder", "type", "saved_to", "width", "height",
        "size_bytes", "source_url"}`` on success, or ``{"error": "<message>"}``.
    """
    return _core_download_image(image_url, subfolder=subfolder, downsize=downsize)




# ═══════════════════════════════════════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def upload_image(
    file_path: str,
    subfolder: str = "agent",
    image_type: str = "input",
    overwrite: bool = False,
) -> dict:
    """Upload an image file to the ComfyUI input directory for use in workflows.

    Args:
        file_path: Local path to the image file.
        subfolder: Subfolder inside the target directory. Defaults to ``agent``
                   so agent-staged inputs are grouped under ``input/agent/``
                   instead of cluttering the input root. ``apply_brainbriefing``
                   qualifies bare LoadImage references with this same subfolder.
        image_type: 'input', 'output', or 'temp' (default 'input').
        overwrite: Overwrite existing file with the same name.
    """
    # Shared with agentY. Two things arrive with it that this host did not have:
    # a bare filename is resolved against ComfyUI's input dir (which is how a
    # canvas LoadImage stores its image), and a file already sitting there is not
    # uploaded a second time.
    return json.dumps(_stage_image(file_path, subfolder=subfolder,
                                   image_type=image_type, overwrite=overwrite))




@tool
def view_image(
    filename: str,
    save_to: str,
    subfolder: str = "",
    image_type: str = "output",
    downsize: bool = True,
) -> object:
    """Download a ComfyUI output image: save the full-resolution original to disk and return a viewable, downsized copy.

    ComfyUI images are frequently larger than Claude can display (the 5 MB /
    1568 px vision limit). This tool always writes the **unresized original** to
    ``save_to`` so you keep the full-quality file, and — when ``downsize`` is True
    (the default) — additionally returns the image downsized to the needed size so
    you can view it inline right here. The original's path is reported in the
    summary so you can reference, re-open, or hand off the full-resolution file.

    Args:
        filename: Image filename on the server e.g. 'ComfyUI_00001_.png'.
        save_to: Local file path to save the full-resolution original. Required.
        subfolder: Optional subfolder where the image is located.
        image_type: Directory type: 'output', 'input', or 'temp'.
        downsize: When True (default), also return the image downsized to Claude's
                  vision limit so it can be viewed inline. Set False to only save
                  the original and return a JSON summary (no inline image).

    Returns:
        When ``downsize`` is True and the file is a still image: a text summary
        (including ``saved_to`` — the path to the unresized original — plus
        dimensions and byte sizes) followed by the downsized image content for
        direct viewing. Otherwise: a JSON summary string.
    """
    try:
        params: dict = {"filename": filename, "type": image_type}
        if subfolder:
            params["subfolder"] = subfolder

        resp = get_client().get("/view", params=params, raw=True)
        content_type = resp.headers.get("content-type", "image/png")
        image_bytes = resp.content

        # Always persist the full-resolution original (the "unresized" file).
        os.makedirs(os.path.dirname(save_to) or ".", exist_ok=True)
        with open(save_to, "wb") as f:
            f.write(image_bytes)

        original_size = len(image_bytes)
        info: dict = {
            "saved_to": save_to,
            "content_type": content_type,
            "size_bytes": original_size,
        }
        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                info["width"], info["height"] = im.size
        except Exception:
            pass

        # Resolve the image format (filename/MIME first, then magic bytes).
        img_fmt = _detect_format(filename, content_type)
        if img_fmt is None:
            if image_bytes[:4] == b"\x89PNG":
                img_fmt = "png"
            elif image_bytes[:3] == b"\xff\xd8\xff":
                img_fmt = "jpeg"
            elif image_bytes[:6] in (b"GIF87a", b"GIF89a"):
                img_fmt = "gif"
            elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
                img_fmt = "webp"

        # Caller opted out, or it isn't a still image we can re-encode → just
        # report the saved original (with a size warning when oversized).
        if not downsize or img_fmt is None:
            if original_size > _MAX_IMAGE_BYTES:
                info["warning"] = (
                    f"Image is {original_size / 1024 / 1024:.1f} MB — exceeds Claude's "
                    "vision limit. Re-run with downsize=True to get a viewable copy."
                )
            return json.dumps(info)

        # Produce a viewable copy within the vision limit while keeping the
        # unresized original on disk. _downsize re-encodes to png/jpeg; normalise
        # exotic containers (gif/webp) to PNG bytes first so PIL can re-save them.
        try:
            if img_fmt in ("png", "jpeg"):
                view_bytes, view_fmt = _downsize(image_bytes, img_fmt)
            else:
                with Image.open(io.BytesIO(image_bytes)) as im:
                    buf = io.BytesIO()
                    im.save(buf, format="PNG")
                view_bytes, view_fmt = _downsize(buf.getvalue(), "png")
        except Exception as exc:
            info["downsize_error"] = str(exc)
            info["warning"] = "Could not produce a downsized copy; original saved only."
            return json.dumps(info)

        dims = (
            f"{info['width']}x{info['height']}, " if "width" in info else ""
        )
        caption = [
            f"Saved full-resolution original to: {save_to}",
            f"Original: {dims}{original_size:,} bytes",
        ]
        if len(view_bytes) < original_size:
            caption.append(
                f"Returned a downsized copy ({len(view_bytes):,} bytes) to fit Claude's "
                "vision limit — the path above is the unresized original."
            )
        return ["\n".join(caption), MCPImage(data=view_bytes, format=view_fmt)]
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_image_resolution(image_path: str) -> str:
    """Return the resolution (width and height in pixels) of a local image file.

    Args:
        image_path: Absolute or relative path to the image file on disk.
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size
        return json.dumps({"width": width, "height": height, "image_path": image_path})
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {image_path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def analyze_image(
    file_path: str = "",
    image_url: str = "",
    question: str = "",
    mode: Literal["describe", "full"] = "describe",
) -> object:
    """Return an image so you can view and analyse it directly.

    Provide either a local ``file_path`` or a public ``image_url`` (not both).
    The image is auto-downsized to satisfy the 5 MB / 1568 px vision limits and
    returned as image content you can see natively — use it to QA a generated
    output against the request, compare an edit against its source, or read a
    web/reference image.

    Supported formats: PNG, JPEG/JPG, GIF, WEBP.

    Args:
        file_path: Absolute or relative path to a local image file.
        image_url: Public http/https URL of an image to download.
        question:  Optional note describing what to focus on; echoed back as a
                   caption (you answer from the returned pixels).
        mode:      Accepted for backward compatibility and ignored — you now view
                   the image directly instead of delegating to a vision sub-model.
    """
    data: Optional[bytes] = None
    source_name = ""
    detected_mime = ""

    if file_path:
        p = Path(file_path).expanduser()
        if not p.exists():
            p = Path(os.getcwd()) / file_path
        if not p.exists():
            return {"status": "error", "content": [{"text": f"File not found: {file_path}"}]}
        source_name = str(p)
        try:
            data = p.read_bytes()
        except Exception as exc:
            return {"status": "error", "content": [{"text": f"Could not read file: {exc}"}]}

    elif image_url:
        source_name = image_url
        try:
            resp = requests.get(image_url, timeout=30)
            resp.raise_for_status()
            detected_mime = resp.headers.get("content-type", "")
            data = resp.content
        except Exception as exc:
            return {"status": "error", "content": [{"text": f"Could not download image: {exc}"}]}

    else:
        return {"status": "error", "content": [{"text": "Provide either file_path or image_url."}]}

    # Detect format
    img_fmt = _detect_format(source_name, detected_mime)
    if img_fmt is None:
        if data[:4] == b"\x89PNG":
            img_fmt = "png"
        elif data[:3] == b"\xff\xd8\xff":
            img_fmt = "jpeg"
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            img_fmt = "gif"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            img_fmt = "webp"
        else:
            return {"status": "error", "content": [{"text": f"Unsupported or undetectable image format for: {source_name}"}]}

    # Downsize if needed
    original_size = len(data)
    _safe_limit = _MAX_IMAGE_BYTES - 64 * 1024  # matches _downsize's _SAFE_IMAGE_BYTES
    try:
        data, img_fmt = _downsize(data, img_fmt)
    except Exception as exc:
        return {"status": "error", "content": [{"text": (
            f"Could not process image from {source_name}: {exc}"
        )}]}
    downsized = len(data) < original_size

    # Hard guard: reject if still over the safe limit (belt-and-suspenders)
    if len(data) > _safe_limit:
        return {"status": "error", "content": [{"text": (
            f"Image from {source_name} could not be reduced to under {_safe_limit:,} bytes "
            f"(final size: {len(data):,} bytes). Try a smaller or simpler image."
        )}]}

    # Return the (downsized) image as MCP image content so the multimodal model
    # can view it directly. ``mode`` is ignored — there is no vision sub-model.
    caption_parts = [
        f"Image from: {source_name}",
        f"Format: {img_fmt.upper()}, {len(data):,} bytes",
    ]
    if downsized:
        caption_parts.append(f"(downsized from {original_size:,} bytes to fit vision limits)")
    if question:
        caption_parts.append(f"Focus: {question}")
    return ["\n".join(caption_parts), MCPImage(data=data, format=img_fmt)]
