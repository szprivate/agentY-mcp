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
    The HF search API tokenises on word boundaries — dots and full extensions
    break tokenisation entirely, so searching with a raw filename like
    ``gemma_3_12B_it_fp4_mixed.safetensors`` returns nothing.  The tool first
    does a single bulk scan of the Comfy-Org HF organisation (which repackages
    models specifically for ComfyUI and includes files like gemma text encoders
    and LTX checkpoints).  If that misses, it falls back to progressively
    broader stem-based queries (full stem → 4-token prefix → 3-token → 2-token
    → hints), verifying each candidate repo's sibling list for an exact match.
    When no exact match exists the tool returns close variants so the agent can
    pick the nearest available file.
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
    """Refresh config/models.json.

    Mirrors the logic in scripts/refresh_models.py so that the in-process
    tool call updates the cache immediately after a download, without needing
    to shell out to the script.
    """
    try:
        from src.utils.comfyui_retrieve_models_customnodes import fetch_available_models
    except Exception as exc:
        logger.warning("_refresh_model_cache: could not import refresh utils: %s", exc)
        return

    try:
        available = fetch_available_models()
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

    Strategy (fully automatic, no agent loop needed):

    Pass 0 – Comfy-Org bulk scan.  A single HF API call with ``author=Comfy-Org``
              and ``full=true`` returns all ~60 Comfy-Org repos with their full
              sibling lists inline.  Comfy-Org repos are curated specifically for
              ComfyUI and are checked first.  Stops here on an exact match.

    The HF search API tokenises on word boundaries — dots and full extensions
    break matching entirely, so passes 1-5 never search with the raw filename.
    Instead, progressively broader queries are built from the filename stem:

    Pass 1 – exact stem (e.g. ``ltx-2.3-22b-dev-fp8``).
    Pass 2 – first 4 hyphen/underscore tokens (``ltx 2 3 22b``).
    Pass 3 – first 3 tokens (``ltx 2 3``).
    Pass 4 – first 2 tokens (``ltx 2``).
    Pass 5 – ``hints`` string alone (if provided).

    Each pass fetches up to 10 candidate repos and checks every candidate's
    sibling list for the exact filename.  Searching stops as soon as at least
    one verified exact match is found.

    If no exact match is found across all passes, the tool returns the best
    *close matches* (files from the same repo whose stem shares a prefix with
    the requested filename) so the agent can make an informed decision.

    Args:
        filename: Exact filename to locate e.g.
            'gemma_3_12B_it_fp4_mixed.safetensors'.
        hints: Optional extra search keywords to narrow / broaden results
            e.g. 'gemma 12b quantized'.  Also used as a dedicated search pass
            when the stem-based passes return nothing.

    Returns:
        JSON ``{"ok": true, "count": N, "matches": [...]}`` where each match
        has ``repo_id``, ``filename``, ``subfolder``, ``url``, and
        ``exact`` (bool).  Feeds directly into ``download_hf_model``.
    """
    def _make_match(repo_id: str, rfilename: str, *, exact: bool) -> dict:
        if "/" in rfilename:
            subfolder, found_name = rfilename.rsplit("/", 1)
        else:
            subfolder, found_name = "", rfilename
        return {
            "repo_id": repo_id,
            "filename": found_name,
            "subfolder": subfolder,
            "url": f"https://huggingface.co/{repo_id}/resolve/main/{rfilename}",
            "exact": exact,
        }

    def _fetch_siblings(model_id: str) -> list[dict]:
        try:
            r = requests.get(
                f"{HF_API_BASE}/{model_id}",
                headers=_hf_headers(),
                timeout=30,
            )
            r.raise_for_status()
            return r.json().get("siblings", [])
        except Exception as exc:
            logger.warning("find_hf_file: could not fetch siblings for %s: %s", model_id, exc)
            return []

    def _search_candidates(query: str, limit: int = 10) -> list[str]:
        """Return list of model_ids from an HF API search."""
        try:
            r = requests.get(
                HF_API_BASE,
                headers=_hf_headers(),
                params={
                    "search": query,
                    "limit": limit,
                    "sort": "downloads",
                    "direction": "-1",
                    "full_text_search": "true",
                },
                timeout=30,
            )
            r.raise_for_status()
            return [m.get("modelId") or m.get("id", "") for m in r.json() if m.get("modelId") or m.get("id")]
        except Exception as exc:
            logger.warning("find_hf_file: search query %r failed: %s", query, exc)
            return []

    def _scan_org_repos(org: str, fname: str, ext: str, stem_prefix: str) -> tuple[list[dict], list[dict]]:
        """Bulk-scan all repos in *org* for *fname* using a single API call.

        Returns (exact_matches, close_matches).
        """
        exact: list[dict] = []
        close: list[dict] = []
        try:
            r = requests.get(
                HF_API_BASE,
                headers=_hf_headers(),
                params={"author": org, "limit": 200, "full": "true"},
                timeout=30,
            )
            r.raise_for_status()
            repos = r.json()
            logger.info("find_hf_file: Comfy-Org scan – %d repos fetched", len(repos))
            for repo in repos:
                mid = repo.get("modelId") or repo.get("id", "")
                if not mid:
                    continue
                found_exact = False
                for sibling in repo.get("siblings", []):
                    rf = sibling.get("rfilename", "")
                    tail = rf.rsplit("/", 1)[-1] if "/" in rf else rf
                    if tail == fname:
                        exact.append(_make_match(mid, rf, exact=True))
                        found_exact = True
                        break
                if not found_exact and ext:
                    for sibling in repo.get("siblings", []):
                        rf = sibling.get("rfilename", "")
                        tail = rf.rsplit("/", 1)[-1] if "/" in rf else rf
                        if tail.endswith("." + ext) and stem_prefix in tail.lower():
                            close.append(_make_match(mid, rf, exact=False))
                            break
        except Exception as exc:
            logger.warning("find_hf_file: Comfy-Org scan failed: %s", exc)
        return exact, close

    # Build stem-based query passes
    stem = filename.rsplit(".", 1)[0]          # strip extension
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    # Normalise to hyphen-separated tokens (underscores and dots become hyphens)
    tokens = [t for t in stem.replace("_", "-").replace(".", "-").split("-") if t]
    stem_prefix = stem[:min(8, len(stem))].replace("_", "-").replace(".", "-").lower()

    queries: list[str] = [stem]  # Pass 1: full stem
    for n in (4, 3, 2):
        if len(tokens) > n:
            q = " ".join(tokens[:n])
            if q not in queries:
                queries.append(q)
    if hints and hints not in queries:
        queries.append(hints)  # Pass 5: hints alone

    close_matches: list[dict] = []
    seen_repos: set[str] = set()
    exact_matches: list[dict] = []

    # ------------------------------------------------------------------
    # Pass 0: Comfy-Org bulk scan (single request, all repos + siblings)
    # ------------------------------------------------------------------
    comfy_exact, comfy_close = _scan_org_repos("Comfy-Org", filename, ext, stem_prefix)
    for m in comfy_exact:
        seen_repos.add(m["repo_id"])
    for m in comfy_close:
        seen_repos.add(m["repo_id"])
    exact_matches.extend(comfy_exact)
    close_matches.extend(comfy_close)

    if exact_matches:
        logger.info("find_hf_file: Comfy-Org exact match found – skipping further passes")
        return json.dumps({"ok": True, "count": len(exact_matches[:5]), "matches": exact_matches[:5]})

    # ------------------------------------------------------------------
    # Passes 1-N: stem-based HF-wide search
    # ------------------------------------------------------------------
    for pass_num, query in enumerate(queries, 1):
        candidates = _search_candidates(query)
        logger.info(
            "find_hf_file: pass %d query=%r → %d candidates",
            pass_num, query, len(candidates),
        )

        for model_id in candidates:
            if model_id in seen_repos:
                continue
            seen_repos.add(model_id)

            siblings = _fetch_siblings(model_id)

            for sibling in siblings:
                rf = sibling.get("rfilename", "")
                tail = rf.rsplit("/", 1)[-1] if "/" in rf else rf

                if tail == filename:
                    exact_matches.append(_make_match(model_id, rf, exact=True))
                    break  # one exact hit per repo is enough

            else:
                # No exact match — look for close variant in same extension
                if ext:
                    for sibling in siblings:
                        rf = sibling.get("rfilename", "")
                        tail = rf.rsplit("/", 1)[-1] if "/" in rf else rf
                        if (
                            tail.endswith("." + ext)
                            and stem_prefix in tail.lower()
                        ):
                            close_matches.append(_make_match(model_id, rf, exact=False))
                            break  # one close match per repo

        if exact_matches:
            logger.info(
                "find_hf_file: found %d exact match(es) on pass %d – stopping",
                len(exact_matches), pass_num,
            )
            break

    # Return exact matches if found, otherwise best close matches (up to 5)
    if exact_matches:
        results = exact_matches[:5]
    else:
        results = close_matches[:5]
        if results:
            logger.info(
                "find_hf_file: no exact match for '%s' – returning %d close variant(s)",
                filename, len(results),
            )
        else:
            logger.info("find_hf_file: no match or close variant found for '%s'", filename)

    return json.dumps({"ok": True, "count": len(results), "matches": results})


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
