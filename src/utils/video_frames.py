"""
agentY – Video frame sampling for Vision QA.

The Vision QA pass (``src/executor._vision_qa``) operates on still images. Kling
multi-shot outputs are videos (``.mp4`` / ``.webm`` / ``.gif`` / ``.mov``), so to
QA a video we sample a handful of representative frames and run the image QA over
those instead.

This module deliberately has **no hard dependency** on any single video library.
It tries several decoder backends in order and degrades gracefully to an empty
result when none is available — callers must treat ``[]`` as "video QA could not
be performed" rather than an error:

    1. imageio (with the imageio-ffmpeg plugin)  ← recommended, see requirements.txt
    2. OpenCV (cv2.VideoCapture)
    3. ffmpeg on PATH (subprocess)

Extracted frames are written as PNGs next to the source video (or into a supplied
output directory) and the list of written paths is returned in temporal order.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("agentY.video_frames")

# Suffixes we treat as video (animated GIF included — its "frames" are still
# sampled the same way so QA can inspect motion endpoints).
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".gif", ".m4v"}


def is_video(path: str | Path) -> bool:
    """Return True when *path* points to a video/animation file (by extension)."""
    return Path(path).suffix.lower() in VIDEO_SUFFIXES


def _evenly_spaced_indices(total: int, count: int) -> list[int]:
    """Return up to *count* frame indices spread across ``[0, total)``.

    Always includes the first and last frame when ``count >= 2`` so QA sees both
    the opening (continuity with the start frame) and the closing state.
    """
    if total <= 0:
        return []
    if count <= 1 or total == 1:
        return [0]
    count = min(count, total)
    if count == 1:
        return [0]
    step = (total - 1) / (count - 1)
    return sorted({int(round(i * step)) for i in range(count)})


def _extract_imageio(video_path: Path, indices_wanted: int, out_dir: Path, stem: str) -> list[Path]:
    import imageio.v3 as iio  # type: ignore

    # Reading the whole stack is simplest and fine here: QA videos are short
    # (<=10s) so memory is not a concern. Returns an ndarray of shape (T,H,W,C).
    frames = iio.imread(video_path)
    try:
        total = int(frames.shape[0])
    except Exception:
        return []
    idxs = _evenly_spaced_indices(total, indices_wanted)
    written: list[Path] = []
    for n, i in enumerate(idxs, 1):
        dest = out_dir / f"{stem}_qa_frame_{n:02d}.png"
        iio.imwrite(dest, frames[i])
        written.append(dest)
    return written


def _extract_opencv(video_path: Path, indices_wanted: int, out_dir: Path, stem: str) -> list[Path]:
    import cv2  # type: ignore

    cap = cv2.VideoCapture(str(video_path))
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        idxs = _evenly_spaced_indices(total, indices_wanted)
        written: list[Path] = []
        for n, i in enumerate(idxs, 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            dest = out_dir / f"{stem}_qa_frame_{n:02d}.png"
            cv2.imwrite(str(dest), frame)
            written.append(dest)
        return written
    finally:
        cap.release()


def _extract_ffmpeg(video_path: Path, indices_wanted: int, out_dir: Path, stem: str) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return []
    # Without probing frame count we sample by an fps filter: pick N frames spread
    # across the clip via the thumbnail/select approach. Simplest reliable route:
    # use -vf "fps" tuned so we land roughly N frames for a short clip, then keep
    # the first N produced. We extract to a temp pattern and rename.
    pattern = out_dir / f"{stem}_qa_frame_%02d.png"
    # fps=2 over a <=10s clip yields up to ~20 frames; we then keep N evenly.
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-vf", "fps=2",
        str(pattern),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120)
    except Exception as exc:  # noqa: BLE001
        logger.debug("video_frames: ffmpeg extraction failed — %s", exc)
        return []
    produced = sorted(out_dir.glob(f"{stem}_qa_frame_*.png"))
    if not produced:
        return []
    idxs = _evenly_spaced_indices(len(produced), indices_wanted)
    keep = {produced[i] for i in idxs}
    # Delete the frames we don't keep to avoid cluttering the output dir.
    for p in produced:
        if p not in keep:
            try:
                p.unlink()
            except Exception:
                pass
    return sorted(keep)


def extract_frames(
    video_path: str | Path,
    *,
    count: int = 3,
    out_dir: str | Path | None = None,
) -> list[Path]:
    """Sample up to *count* evenly-spaced frames from *video_path* as PNG files.

    Tries imageio → OpenCV → ffmpeg in order. Returns the written frame paths in
    temporal order, or ``[]`` when the file is missing or no decoder backend is
    available (callers should treat ``[]`` as "video QA unavailable").

    Args:
        video_path: Path to the source video/animation file.
        count:      Number of frames to sample (first + last always included when
                    ``count >= 2``). Defaults to 3 (open / middle / close).
        out_dir:    Directory to write frames into. Defaults to the video's
                    parent directory.
    """
    src = Path(video_path)
    if not src.exists():
        logger.warning("video_frames: source not found: %s", src)
        return []

    dest_dir = Path(out_dir) if out_dir else src.parent
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        dest_dir = src.parent
    stem = src.stem

    for name, fn in (("imageio", _extract_imageio), ("opencv", _extract_opencv), ("ffmpeg", _extract_ffmpeg)):
        try:
            frames = fn(src, count, dest_dir, stem)
            if frames:
                logger.info("video_frames: extracted %d frame(s) from %s via %s", len(frames), src.name, name)
                return frames
        except ImportError:
            continue
        except Exception as exc:  # noqa: BLE001
            logger.debug("video_frames: backend %s failed for %s — %s", name, src.name, exc)
            continue

    logger.warning(
        "video_frames: no working decoder backend (imageio/opencv/ffmpeg) for %s — "
        "video QA will be skipped. Install 'imageio[ffmpeg]' to enable it.",
        src.name,
    )
    return []
