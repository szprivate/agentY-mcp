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
import re
import uuid
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

# Anthropic's API limit is 5 MB applied to the BASE64-ENCODED image.
# Strands sends images as base64, which inflates raw bytes by ~33% (4/3 factor).
# To stay safely under the 5 MB base64 limit: 5 MB * 0.72 ≈ 3.6 MB raw.
_MAX_IMAGE_BYTES = int(5 * 1024 * 1024 * 0.72)   # ~3.6 MB raw → ~4.8 MB base64
_OPTIMAL_LONG_EDGE = 1568            # Claude resizes beyond this anyway

_FORMAT_MAP: dict[str, str] = {
    "png":  "png",
    "jpg":  "jpeg",
    "jpeg": "jpeg",
    "gif":  "gif",
    "webp": "webp",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_format(path_or_name: str, mime: str = "") -> Optional[str]:
    """Resolve the Strands image format string from a filename or MIME type."""
    ext = Path(path_or_name).suffix.lstrip(".").lower()
    fmt = _FORMAT_MAP.get(ext)
    if fmt:
        return fmt
    if mime.startswith("image/"):
        sub = mime.split("/")[-1].lower()
        return _FORMAT_MAP.get(sub)
    return None


def _downsize(data: bytes, img_fmt: str) -> tuple[bytes, str]:
    """Downsize image in-memory to fit Claude API constraints.

    Caps long edge at 1568 px and enforces the 5 MB hard limit.
    Uses a small internal safety margin (_SAFE_IMAGE_BYTES) so images
    never land exactly on the boundary.

    Returns:
        (image_bytes, actual_format) where actual_format may differ from
        img_fmt if the image was converted (e.g. PNG → JPEG) to meet size limits.
    """
    _SAFE_IMAGE_BYTES = _MAX_IMAGE_BYTES - 64 * 1024  # small headroom; _MAX_IMAGE_BYTES already base64-adjusted

    if len(data) <= _SAFE_IMAGE_BYTES:
        img = Image.open(io.BytesIO(data))
        if max(img.width, img.height) <= _OPTIMAL_LONG_EDGE:
            return data, img_fmt

    img = Image.open(io.BytesIO(data))
    long_edge = max(img.width, img.height)

    if long_edge > _OPTIMAL_LONG_EDGE:
        ratio = _OPTIMAL_LONG_EDGE / long_edge
        new_w, new_h = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    pil_fmt = "PNG" if img_fmt == "png" else "JPEG"
    if img.mode == "RGBA" and pil_fmt == "JPEG":
        img = img.convert("RGB")

    buf = io.BytesIO()
    quality = 90
    while quality >= 20:
        buf.seek(0)
        buf.truncate()
        if pil_fmt == "JPEG":
            if img.mode not in ("RGB", "L", "CMYK"):
                img = img.convert("RGB")
            img.save(buf, format=pil_fmt, quality=quality, optimize=True)
        else:
            img.save(buf, format=pil_fmt, optimize=True)
        # Use len(getvalue()) — not buf.tell() — because PIL's optimize=True JPEG
        # encoding performs a Huffman-table seek pass that can leave the cursor at
        # a position other than end-of-file, making tell() an unreliable size proxy.
        if len(buf.getvalue()) <= _SAFE_IMAGE_BYTES:
            break
        if pil_fmt == "PNG":
            pil_fmt = "JPEG"
            if img.mode not in ("RGB", "L", "CMYK"):
                img = img.convert("RGB")
            continue
        quality -= 10

    # Hard fallback: if the quality loop wasn't enough, halve dimensions
    # progressively until the image fits.  Converts to JPEG at quality=20
    # which is always far smaller than a lossless format at any resolution.
    while len(buf.getvalue()) > _SAFE_IMAGE_BYTES and max(img.width, img.height) >= 128:
        new_w = max(1, img.width // 2)
        new_h = max(1, img.height // 2)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=20, optimize=True)
        pil_fmt = "JPEG"

    result = buf.getvalue()
    # Final safety net: if somehow still too large, return a guaranteed-small thumbnail.
    # Use _SAFE_IMAGE_BYTES (not _MAX_IMAGE_BYTES) so we always enforce the conservative limit.
    if len(result) > _SAFE_IMAGE_BYTES:
        img = img.resize((max(1, img.width // 4), max(1, img.height // 4)), Image.LANCZOS)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        emergency_buf = io.BytesIO()
        img.save(emergency_buf, format="JPEG", quality=20, optimize=True)
        result = emergency_buf.getvalue()
        pil_fmt = "JPEG"

    # Map PIL format name back to the Strands format string
    actual_fmt = "jpeg" if pil_fmt == "JPEG" else "png"
    return result, actual_fmt


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
    try:
        if not os.path.isfile(file_path):
            return json.dumps({"error": f"File not found: {file_path}"})

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"image": (filename, f, "image/png")}
            data = {"type": image_type, "overwrite": str(overwrite).lower()}
            if subfolder:
                data["subfolder"] = subfolder
            return json.dumps(get_client().post("/upload/image", data=data, files=files))
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def download_image(image_url: str, subfolder: str = "agent/references", downsize: bool = True) -> str:
    """Download a web image straight into ComfyUI's input folder so a workflow can load it.

    Use this right after ``web_search_images`` to fetch a reference image you
    found (pass the result's ``image_url``).  The image is uploaded into ComfyUI's
    input directory under ``agent/references`` and can then be referenced directly
    by a ``LoadImage`` node using the returned ``name`` and ``subfolder`` — no
    separate ``upload_image`` call is needed.

    A browser User-Agent is sent so hosts that block hot-linking still serve the
    file.

    Args:
        image_url: Direct http/https URL of the image (the ``image_url`` field
                   returned by ``web_search_images``).
        subfolder: Input-dir subfolder to store the image in. Defaults to
                   ``agent/references``.
        downsize:  When True (default), oversized images are downscaled to the
                   pipeline's 5 MB / 1568 px limit so they stay usable everywhere
                   (matches how user-uploaded images are handled).  Set False to
                   keep the original full-resolution file.

    Returns:
        JSON ``{"name", "subfolder", "type", "saved_to", "width", "height",
        "size_bytes", "source_url"}`` on success, or ``{"error": "<message>"}``.
        ``name`` + ``subfolder`` are what a ``LoadImage`` node references;
        ``saved_to`` is the resolved on-disk path (for ``analyze_image`` etc.).
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
        }
        resp = requests.get(image_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.content
        mime = resp.headers.get("content-type", "")

        # Resolve image format from content-type / URL extension, then magic bytes.
        img_fmt = _detect_format(image_url.split("?")[0], mime)
        if img_fmt is None:
            if data[:4] == b"\x89PNG":
                img_fmt = "png"
            elif data[:3] == b"\xff\xd8\xff":
                img_fmt = "jpeg"
            elif data[:6] in (b"GIF87a", b"GIF89a"):
                img_fmt = "gif"
            elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                img_fmt = "webp"
        if img_fmt is None:
            return json.dumps(
                {"error": f"URL did not return a recognised image (content-type={mime!r})."}
            )

        # Optionally normalise to the pipeline's size/edge limits. _downsize only
        # targets png/jpeg; gif/webp are uploaded as-is.
        ext = img_fmt
        if downsize and img_fmt in ("png", "jpeg"):
            try:
                data, ext = _downsize(data, img_fmt)
            except Exception:
                ext = img_fmt  # keep original bytes if downsizing fails

        suffix = "jpg" if ext == "jpeg" else ext
        base = image_url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(base).stem)[:48] or "reference"
        filename = f"{stem}_{uuid.uuid4().hex[:8]}.{suffix}"

        # Upload into ComfyUI's input dir via the API (filesystem-agnostic; works
        # whether ComfyUI is local or remote).  ComfyUI creates the subfolder and
        # returns the authoritative {name, subfolder, type}.
        files = {"image": (filename, io.BytesIO(data), f"image/{ext}")}
        form: dict = {"type": "input", "overwrite": "false"}
        if subfolder:
            form["subfolder"] = subfolder
        up = get_client().post("/upload/image", data=form, files=files)
        if not isinstance(up, dict) or "name" not in up:
            return json.dumps({"error": f"Unexpected /upload/image response: {up!r}"})

        # Best-effort resolve the on-disk path for analyze_image/get_image_resolution.
        saved_to = ""
        try:
            from src.tools.comfyui import get_comfyui_dirs  # lazy: avoid import cycle
            input_dir = json.loads(get_comfyui_dirs()).get("input_dir", "")
            if input_dir and input_dir != "unknown":
                saved_to = str(Path(input_dir) / up.get("subfolder", "") / up["name"])
        except Exception:
            pass

        try:
            with Image.open(io.BytesIO(data)) as im:
                width, height = im.size
        except Exception:
            width = height = None

        return json.dumps(
            {
                "name": up.get("name"),
                "subfolder": up.get("subfolder", subfolder),
                "type": up.get("type", "input"),
                "saved_to": saved_to,
                "width": width,
                "height": height,
                "size_bytes": len(data),
                "source_url": image_url,
            }
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


@tool
def view_image(
    filename: str,
    save_to: str,
    subfolder: str = "",
    image_type: str = "output",
) -> str:
    """Download an image from the ComfyUI output directory and save it to a local path.

    After saving, use analyze_image(file_path=save_to) to inspect the image
    contents.

    Args:
        filename: Image filename on the server e.g. 'ComfyUI_00001_.png'.
        save_to: Local file path to save the image. Required.
        subfolder: Optional subfolder where the image is located.
        image_type: Directory type: 'output', 'input', or 'temp'.
    """
    try:
        params: dict = {"filename": filename, "type": image_type}
        if subfolder:
            params["subfolder"] = subfolder

        resp = get_client().get("/view", params=params, raw=True)
        content_type = resp.headers.get("content-type", "image/png")
        image_bytes = resp.content

        os.makedirs(os.path.dirname(save_to) or ".", exist_ok=True)
        with open(save_to, "wb") as f:
            f.write(image_bytes)
        result = {
            "saved_to": save_to,
            "content_type": content_type,
            "size_bytes": len(image_bytes),
        }
        if len(image_bytes) > 5 * 1024 * 1024:
            result["warning"] = (
                f"Image is {len(image_bytes) / 1024 / 1024:.1f} MB — exceeds 5 MB limit. "
                "Activate the 'image-downsize' skill to produce a smaller copy."
            )
        return json.dumps(result)
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
