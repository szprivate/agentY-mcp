"""
Hugging Face integration tools for agentY.

Provides @tool-decorated functions for discovering and downloading models
from the Hugging Face Hub via its HTTP API.

Environment variables:
    HF_TOKEN            – Hugging Face access token (required for gated models)
    COMFYUI_MODELS_DIR  – Base directory where ComfyUI stores models
                          (falls back to config/settings.json → comfyui_models_dir,
                           then to the sensible default D:/AI/ComfyUI/models)

Note on ``find_hf_file``:
    The HF search API only indexes repo names and metadata, not individual file
    listings.  Filename-specific lookups — especially community quantizations
    (e.g. ``gemma_3_12B_it_fp4_mixed.safetensors``) — therefore need a web-
    search fallback.  ``find_hf_file`` tries the HF API first and falls back
    to a DuckDuckGo HTML search when the API returns nothing useful.
"""

import io
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

from src.utils.model_node_mapping import NODE_TO_FOLDER, get_storage_path
from src.utils.progress_signal import push as _push_progress
from src.utils.secrets import get_secret
from strands import tool

logger = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co/api/models"



def _hf_headers() -> dict:
    """Return request headers including HF auth token if available."""
    headers = {"Accept": "application/json"}
    token = get_secret("HF_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _models_base_dir() -> Path:
    """Resolve the ComfyUI models base directory.

    Priority:
    1. COMFYUI_MODELS_DIR env var
    2. comfyui_models_dir key in config/settings.json
    3. Default: D:/AI/ComfyUI/models
    """
    env_dir = get_secret("COMFYUI_MODELS_DIR")
    if env_dir:
        return Path(env_dir)

    config_path = Path(__file__).parent.parent.parent / "config" / "settings.json"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.loads("".join(ln for ln in f if not ln.lstrip().startswith("//")))
            d = config.get("comfyui_models_dir")
            if d:
                return Path(d)
            base = config.get("comfyui_base_dir")
            if base:
                return Path(base) / "models"
        except Exception:
            pass

    return Path("D:/AI/ComfyUI/models")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _refresh_model_cache() -> None:
    """Refresh config/models.json and config/custom_nodes.json.

    Mirrors the logic in scripts/refresh_models.py so that the in-process
    tool call updates the cache immediately after a download, without needing
    to shell out to the script.
    """
    try:
        from src.utils.comfyui_retrieve_models_customnodes import (
            fetch_available_models,
            fetch_custom_node_names,
        )
    except Exception as exc:
        logger.warning("_refresh_model_cache: could not import refresh utils: %s", exc)
        return

    try:
        available = fetch_available_models()
        custom_node_names = fetch_custom_node_names()
    except Exception as exc:
        logger.warning("_refresh_model_cache: ComfyUI unreachable – skipping cache refresh: %s", exc)
        return

    project_root = Path(__file__).parent.parent.parent.resolve()

    models_path = project_root / "config" / "models.json"
    if models_path.exists():
        try:
            raw = "".join(ln for ln in models_path.read_text(encoding="utf-8").splitlines(keepends=True)
                          if not ln.lstrip().startswith("//"))
            models_data = json.loads(raw) if raw.strip() else {}
        except Exception:
            models_data = {}
    else:
        models_data = {}

    models_data["available"] = available
    with open(models_path, "w", encoding="utf-8") as f:
        json.dump(models_data, f, indent=2)

    total = sum(len(v) for v in available.values() if isinstance(v, list))
    logger.info("[refresh_models] models.json refreshed – %d folders, %d files", len(available), total)

    if custom_node_names:
        cn_path = project_root / "config" / "custom_nodes.json"
        with open(cn_path, "w", encoding="utf-8") as f:
            json.dump({"custom_nodes": custom_node_names}, f, indent=2)
        logger.info("[refresh_models] custom_nodes.json refreshed – %d nodes", len(custom_node_names))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
def search_huggingface_models(
    query: str,
    filter_tag: str = "",
    limit: int = 10,
    full_text_search: bool = False,
) -> str:
    """Search the Hugging Face Hub for models by keyword.

    Args:
        query: Search string e.g. 'flux lora', 'wan2.1 video'.
        filter_tag: Optional pipeline/library tag e.g. 'diffusers', 'flux'.
        limit: Max results (default 10, max 50).
        full_text_search: When True, enables full-text search so the query also
            matches README / model card content — useful when a specific
            filename is referenced in a model card but not in the repo name
            (e.g. community quantization files).
    """
    try:
        params: dict = {
            "search": query,
            "limit": min(limit, 50),
            "sort": "downloads",
            "direction": "-1",
        }
        if filter_tag:
            params["filter"] = filter_tag
        if full_text_search:
            params["full_text_search"] = "true"

        resp = requests.get(
            HF_API_BASE,
            headers=_hf_headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        models = resp.json()

        results = []
        for m in models:
            results.append({
                "model_id": m.get("modelId") or m.get("id", ""),
                "downloads": m.get("downloads", 0),
                "likes": m.get("likes", 0),
                "pipeline_tag": m.get("pipeline_tag", ""),
                "tags": m.get("tags", []),
                "last_modified": m.get("lastModified", ""),
            })

        return json.dumps({"ok": True, "count": len(results), "models": results})
    except requests.HTTPError as exc:
        logger.error("HF API HTTP error in search: %s", exc)
        return json.dumps({"ok": False, "error": f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"})
    except Exception as exc:
        logger.error("Error in search_huggingface_models: %s", exc, exc_info=True)
        return json.dumps({"ok": False, "error": str(exc)})


@tool
def find_hf_file(filename: str, hints: str = "") -> str:
    """Locate which Hugging Face repo(s) host a specific file.

    Useful for finding community quantizations or obscure model files whose
    repo name does not obviously match the filename.

    Strategy:
    1. Full-text HF API search (matches model card / README content).
       For each candidate, verify the file appears in the repo's sibling list.
    2. DuckDuckGo web-search fallback for cases the HF API still misses.

    Args:
        filename: Exact filename to locate e.g.
            'gemma_3_12B_it_fp4_mixed.safetensors'.
        hints: Optional extra search keywords to narrow results e.g.
            'gemma 12b quantized'.

    Returns:
        JSON with ``matches`` list, each entry containing ``repo_id``,
        ``filename``, ``subfolder``, and ``url`` — ready to pass directly
        to ``download_hf_model``.
    """
    import re
    from urllib.parse import quote_plus

    matches: list[dict] = []

    # ------------------------------------------------------------------
    # Step 1: HF API full-text search
    # ------------------------------------------------------------------
    try:
        search_query = f"{filename} {hints}".strip()
        params: dict = {
            "search": search_query,
            "limit": 5,
            "sort": "downloads",
            "direction": "-1",
            "full_text_search": "true",
        }
        resp = requests.get(
            HF_API_BASE,
            headers=_hf_headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        candidates = resp.json()

        for candidate in candidates:
            model_id = candidate.get("modelId") or candidate.get("id", "")
            if not model_id:
                continue
            try:
                info_resp = requests.get(
                    f"{HF_API_BASE}/{model_id}",
                    headers=_hf_headers(),
                    timeout=30,
                )
                info_resp.raise_for_status()
                info = info_resp.json()
            except requests.HTTPError as exc:
                logger.warning("find_hf_file: could not fetch info for %s: %s", model_id, exc)
                continue
            except Exception as exc:
                logger.warning("find_hf_file: unexpected error fetching info for %s: %s", model_id, exc)
                continue

            for sibling in info.get("siblings", []):
                rfilename = sibling.get("rfilename", "")
                if rfilename.endswith("/" + filename) or rfilename == filename:
                    # Extract optional subfolder
                    if "/" in rfilename:
                        subfolder = rfilename.rsplit("/", 1)[0]
                        found_name = rfilename.rsplit("/", 1)[1]
                    else:
                        subfolder = ""
                        found_name = rfilename
                    url = f"https://huggingface.co/{model_id}/resolve/main/{rfilename}"
                    matches.append({
                        "repo_id": model_id,
                        "filename": found_name,
                        "subfolder": subfolder,
                        "url": url,
                    })
                    break  # one match per repo is enough
    except requests.HTTPError as exc:
        logger.warning("find_hf_file: HF API search failed (%s) – trying web fallback", exc)
    except Exception as exc:
        logger.warning("find_hf_file: HF API step error: %s", exc)

    # ------------------------------------------------------------------
    # Step 2: DuckDuckGo web-search fallback
    # ------------------------------------------------------------------
    if not matches:
        try:
            ddg_query = f"site:huggingface.co {filename} {hints}".strip()
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(ddg_query)}"
            ddg_resp = requests.get(
                ddg_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
                timeout=30,
            )
            ddg_resp.raise_for_status()

            # Extract HF blob/resolve URLs from the raw HTML
            pattern = re.compile(
                r"https://huggingface\.co/"
                r"([\w\-\.]+/[\w\-\.]+)"
                r"/(?:blob|resolve)/main/"
                r"([^\s\"'>]+)"
            )
            seen: set[str] = set()
            for repo_path, file_path in pattern.findall(ddg_resp.text):
                if len(matches) >= 5:
                    break
                # Only keep hits where the filename actually matches
                tail = file_path.split("/")[-1]
                if tail != filename:
                    continue
                key = f"{repo_path}|{file_path}"
                if key in seen:
                    continue
                seen.add(key)

                if "/" in file_path:
                    subfolder = file_path.rsplit("/", 1)[0]
                    found_name = file_path.rsplit("/", 1)[1]
                else:
                    subfolder = ""
                    found_name = file_path

                url = f"https://huggingface.co/{repo_path}/resolve/main/{file_path}"
                matches.append({
                    "repo_id": repo_path,
                    "filename": found_name,
                    "subfolder": subfolder,
                    "url": url,
                })
        except requests.HTTPError as exc:
            logger.error("find_hf_file: DuckDuckGo search HTTP error: %s", exc)
            return json.dumps({"ok": False, "error": f"Web fallback HTTP {exc.response.status_code}: {exc.response.text[:300]}"})
        except Exception as exc:
            logger.error("find_hf_file: DuckDuckGo search error: %s", exc, exc_info=True)
            return json.dumps({"ok": False, "error": str(exc)})

    return json.dumps({"ok": True, "count": len(matches), "matches": matches})


@tool
def get_model_info(model_id: str) -> str:
    """Fetch metadata and file list for a specific Hugging Face model.

    Args:
        model_id: HF model identifier e.g. 'black-forest-labs/FLUX.1-dev'.
    """
    try:
        url = f"{HF_API_BASE}/{model_id}"
        resp = requests.get(url, headers=_hf_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Extract the file listing from siblings
        files = []
        for s in data.get("siblings", []):
            files.append({
                "filename": s.get("rfilename", ""),
                "size": s.get("size"),
            })

        result = {
            "ok": True,
            "model_id": data.get("modelId") or data.get("id", model_id),
            "pipeline_tag": data.get("pipeline_tag", ""),
            "tags": data.get("tags", []),
            "license": data.get("cardData", {}).get("license", "unknown") if isinstance(data.get("cardData"), dict) else "unknown",
            "gated": data.get("gated", False),
            "downloads": data.get("downloads", 0),
            "likes": data.get("likes", 0),
            "last_modified": data.get("lastModified", ""),
            "files": files,
        }
        return json.dumps(result)
    except requests.HTTPError as exc:
        logger.error("HF API HTTP error in get_model_info: %s", exc)
        return json.dumps({"ok": False, "error": f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"})
    except Exception as exc:
        logger.error("Error in get_model_info: %s", exc, exc_info=True)
        return json.dumps({"ok": False, "error": str(exc)})


@tool
def download_hf_model(
    model_id: str,
    filename: str,
    node_class_type: str = "",
    destination_folder: str = "",
    subfolder: str = "",
) -> str:
    """Download a file from a HuggingFace repo. Check model availability with check_model first.

    Prefer supplying *node_class_type* (the ComfyUI class name of the node that
    references the model, e.g. ``"UNETLoader"``).  The correct storage folder is
    then derived automatically via the NODE_TO_FOLDER mapping.  If
    *node_class_type* is unknown or omitted, fall back to *destination_folder*
    (relative path under the models base dir, e.g. ``"FLUX1"``).

    Args:
        model_id: HF model ID e.g. 'black-forest-labs/FLUX.1-dev'.
        filename: File to download e.g. 'flux1-dev.safetensors'.
        node_class_type: ComfyUI node class that loads this model
            e.g. 'UNETLoader', 'CheckpointLoaderSimple', 'LoraLoader'.
            Used to resolve the correct model sub-folder automatically.
        destination_folder: Fallback – target subfolder under models dir
            e.g. 'FLUX1'.  Ignored when *node_class_type* is provided.
        subfolder: Subfolder within the HF repo e.g. 'transformer'.
    """
    try:
        base = _models_base_dir()

        # Resolve destination: prefer node_class_type → get_storage_path,
        # fall back to explicit destination_folder, else place in models root.
        if node_class_type:
            try:
                comfyui_base = str(base.parent)
                full_path = get_storage_path(node_class_type, filename, comfyui_base)
                dest_path = Path(full_path)
            except ValueError as mapping_err:
                logger.warning(
                    "node_class_type %r not in NODE_TO_FOLDER (%s); "
                    "falling back to destination_folder.",
                    node_class_type, mapping_err,
                )
                dest_path = base / (destination_folder or "") / filename
        elif destination_folder:
            dest_path = base / destination_folder / filename
        else:
            dest_path = base / filename

        dest_dir = dest_path.parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Safety: don't re-download if already present
        if dest_path.exists():
            return json.dumps({
                "ok": True,
                "path": str(dest_path),
                "message": "File already exists — skipping download.",
                "size_mb": round(dest_path.stat().st_size / (1024 * 1024), 2),
            })

        # Build the download URL
        if subfolder:
            url = f"https://huggingface.co/{model_id}/resolve/main/{subfolder}/{filename}"
        else:
            url = f"https://huggingface.co/{model_id}/resolve/main/{filename}"

        headers = {}
        token = get_secret("HF_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.info("Downloading %s from %s …", filename, model_id)
        _push_progress(f"⬇️ Starting download: **{filename}** from `{model_id}`")

        resp = requests.get(url, headers=headers, stream=True, timeout=60)
        resp.raise_for_status()

        total_size = int(resp.headers.get("content-length", 0))
        chunk_size = 8 * 1024 * 1024  # 8 MB chunks

        # --- tqdm setup -------------------------------------------------
        # _TqdmSignalWriter intercepts tqdm's output, strips ANSI / carriage
        # returns, and pushes each refreshed bar line to the progress signal
        # (visible in Chainlit) as well as writing to the real stderr
        # (visible in the terminal).
        class _TqdmSignalWriter(io.RawIOBase):
            """File-like wrapper that tees tqdm output to progress_signal."""

            def __init__(self, real_file):
                self._real = real_file
                self._last_pushed: str = ""

            def write(self, s: str) -> int:  # tqdm always passes str
                self._real.write(s)
                # Strip carriage-returns / ANSI escapes to get a clean line.
                clean = s.replace("\r", "").replace("\n", "").strip()
                # Remove ANSI escape codes (colours)
                import re as _re
                clean = _re.sub(r"\x1b\[[0-9;]*m", "", clean)
                if clean and clean != self._last_pushed:
                    self._last_pushed = clean
                    _push_progress(f"⬇️ [{clean}]")
                return len(s)

            def flush(self) -> None:
                self._real.flush()

        _tqdm_writer = _TqdmSignalWriter(sys.stderr)

        # Write to a temp file first, rename on completion
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".downloading")
        try:
            with open(tmp_path, "wb") as f, tqdm(
                total=total_size if total_size > 0 else None,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=filename,
                file=_tqdm_writer,
                dynamic_ncols=False,
                ncols=60,
                leave=True,
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

            # Rename temp → final
            tmp_path.rename(dest_path)
        except Exception:
            # Clean up partial file on error
            if tmp_path.exists():
                tmp_path.unlink()
            raise

        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)

        # Refresh the model cache so check_model sees the new file immediately.
        logger.info("[download_hf_model] Refreshing model cache after download…")
        _refresh_model_cache()

        return json.dumps({
            "ok": True,
            "path": str(dest_path),
            "size_mb": size_mb,
            "message": f"Downloaded {filename} ({size_mb} MB) to {dest_dir}/",
        })
    except requests.HTTPError as exc:
        status = exc.response.status_code
        body = exc.response.text[:400]
        logger.error("HF download HTTP error: %s %s", status, body)
        if status == 401:
            hint = " — Is HF_TOKEN set and authorised for this gated model?"
        elif status == 403:
            hint = " — Access denied. You may need to accept the model's license on HF."
        elif status == 404:
            hint = " — File not found. Check model_id, subfolder, and filename."
        else:
            hint = ""
        return json.dumps({"ok": False, "error": f"HTTP {status}{hint}: {body}"})
    except Exception as exc:
        logger.error("Error in download_hf_model: %s", exc, exc_info=True)
        return json.dumps({"ok": False, "error": str(exc)})
