"""
agentY – workflow executor.

After a ComfyUI workflow is assembled and validated, the orchestrator calls
``signal_workflow_ready(workflow_path)``.  The pipeline then calls
``execute_workflow()`` (single) or ``execute_workflows_batch()`` (batch), which:

1. Submits the workflow(s) to ComfyUI (``POST /prompt``).
   Batch: ALL workflows are submitted before any polling begins, so
   ComfyUI can start working on the queue immediately.
2. Polls until execution completes (zero LLM tokens burned during the wait).
   Batch: polls each prompt_id in submission order; earlier jobs are
   typically already done by the time we reach them.
3. Copies every output file from ComfyUI's configured output directory to
   the path specified in the brainbriefing (``output_nodes[].output_path``).
   Falls back to downloading via ``/view`` when the output directory cannot be
   determined from the ComfyUI API.
4. Returns the output image(s) (or sampled video frames) so the host model
   (Claude) can inspect the result against the original brainbriefing.

Usage
-----
    async for status_line in execute_workflow(path, brainbriefing_json):
        print(status_line)

    async for status_line in execute_workflows_batch(paths, brainbriefing_json):
        print(status_line)

Both functions are ``AsyncGenerator[str, None]`` so the pipeline can forward
each status update to the UI in real time.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger("agentY.executor")


def _project_root() -> Path:
    return Path(__file__).parent.parent.resolve()


def _load_config() -> dict:
    config_path = _project_root() / "config" / "settings.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.loads("".join(ln for ln in f if not ln.lstrip().startswith("//")))
    return {}


def _output_dir() -> Path:
    """Return the fallback directory where ComfyUI output files are saved."""
    cfg = _load_config()
    od = cfg.get("output_dir", "./output/")
    return (_project_root() / od).resolve()


# --- ComfyUI dir cache -----------------------------------------------------
# /system_stats returns ComfyUI's argv, which is constant for the lifetime of
# the server process.  Both --output-directory and --user-directory are parsed
# from a single response and memoised so per-output-file resolution doesn't
# trigger a new HTTP roundtrip every call.  Reset via _reset_comfyui_dir_cache
# (e.g. when the user restarts ComfyUI from the agent UI).
_COMFYUI_DIR_CACHE_LOADED: bool = False
_COMFYUI_OUTPUT_DIR: Path | None = None
_COMFYUI_USER_DIR: Path | None = None


def _reset_comfyui_dir_cache() -> None:
    global _COMFYUI_DIR_CACHE_LOADED, _COMFYUI_OUTPUT_DIR, _COMFYUI_USER_DIR
    _COMFYUI_DIR_CACHE_LOADED = False
    _COMFYUI_OUTPUT_DIR = None
    _COMFYUI_USER_DIR = None


def _load_comfyui_dirs() -> None:
    global _COMFYUI_DIR_CACHE_LOADED, _COMFYUI_OUTPUT_DIR, _COMFYUI_USER_DIR
    if _COMFYUI_DIR_CACHE_LOADED:
        return
    try:
        from src.utils.comfyui_client import get_client, parse_argv_dir_flag

        stats = get_client().get("/system_stats")
        argv = stats.get("system", {}).get("argv", []) if isinstance(stats, dict) else []
        out_dir = parse_argv_dir_flag(argv, "--output-directory")
        if out_dir:
            _COMFYUI_OUTPUT_DIR = Path(out_dir).resolve()
        usr_dir = parse_argv_dir_flag(argv, "--user-directory")
        if usr_dir:
            _COMFYUI_USER_DIR = Path(usr_dir).resolve()
    except Exception as exc:
        logger.debug("executor: could not query ComfyUI dirs — %s", exc)
    _COMFYUI_DIR_CACHE_LOADED = True


def _get_comfyui_output_dir() -> Path | None:
    """Return ComfyUI's --output-directory (cached for the process lifetime)."""
    _load_comfyui_dirs()
    return _COMFYUI_OUTPUT_DIR


def _get_comfyui_user_dir() -> Path | None:
    """Return ComfyUI's --user-directory (cached for the process lifetime)."""
    _load_comfyui_dirs()
    return _COMFYUI_USER_DIR


# _archive_input_images removed: input files are uploaded to ComfyUI via the
# upload_image tool and live in ComfyUI's --input-directory; no secondary copy
# is needed.  The upload filename is captured in the conversation history and
# summarised into INPUT_PATHS so subsequent sessions can reference it.


def _copy_workflow_to_user_dir(workflow_path: str) -> None:
    """Copy the finished workflow JSON to the ComfyUI user directory.

    Destination: ``{user_dir}/workflows/``.
    The user directory is resolved from the ``--user-directory=`` flag via
    ``/system_stats``.  Falls back to ``comfyui_user_dir`` in settings.json.
    Silently skips when the workflow file doesn't exist.
    """
    import shutil

    src = Path(workflow_path)
    if not src.exists():
        logger.debug("executor: _copy_workflow_to_user_dir: source not found: %s", workflow_path)
        return

    user_dir = _get_comfyui_user_dir()
    if user_dir is None:
        cfg = _load_config()
        fallback = cfg.get("comfyui_user_dir", "")
        if fallback:
            user_dir = Path(fallback).resolve()
        else:
            logger.debug("executor: _copy_workflow_to_user_dir: no user dir configured, skipping")
            return

    dest_dir = user_dir / "workflows"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    try:
        shutil.copy2(src, dest)
        logger.info("executor: workflow copied to user dir → %s", dest)
    except Exception as exc:
        logger.warning("executor: could not copy workflow to user dir — %s", exc)


# _resolve_brainbriefing_output_dir removed: output files are now always kept
# in ComfyUI's --output-directory; _resolve_output_path returns their
# authoritative on-disk path directly from /system_stats without copying.


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_node_titles(workflow_path: str) -> dict[str, str]:
    """Return a mapping of node_id -> display name for the given workflow.

    The display name is ``_meta.title`` when present, otherwise ``class_type``.
    Returns an empty dict on any error.
    """
    try:
        p = Path(workflow_path)
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        titles: dict[str, str] = {}
        for node_id, node_data in data.items():
            if not isinstance(node_data, dict):
                continue
            title = node_data.get("_meta", {}).get("title", "") or node_data.get("class_type", "")
            if title:
                titles[str(node_id)] = title
        return titles
    except Exception:
        return {}


def _submit_workflow(workflow_path: str, client_id: str = "") -> str:
    """Submit *workflow_path* to ComfyUI and return the ``prompt_id``.

    When *client_id* is provided it is forwarded so the matching WebSocket
    connection receives this prompt's progress events.

    Raises ``RuntimeError`` on failure.
    """
    from src.utils.comfyui_client import get_client

    p = Path(workflow_path)
    if not p.exists():
        raise RuntimeError(f"Workflow file not found: {workflow_path}")

    workflow = json.loads(p.read_text(encoding="utf-8"))
    client = get_client()
    payload: dict = {"prompt": workflow}
    if client_id:
        payload["client_id"] = client_id
    if client.api_key:
        payload["extra_data"] = {"api_key_comfy_org": client.api_key}

    result = client.post("/prompt", json_data=payload)
    if isinstance(result, dict) and "prompt_id" in result:
        return result["prompt_id"]
    raise RuntimeError(f"Unexpected response from ComfyUI /prompt: {result!r}")


def _extract_output_files(history: dict) -> list[dict]:
    """Return a flat list of ``{"filename", "subfolder", "type", "node_id"}`` dicts
    from a stripped history response.

    Handles the ``_strip_history`` output format where outputs are nested under
    ``{prompt_id: {"outputs": {node_id: {"images": [...], "gifs": [...], ...}}}}`.
    """
    files: list[dict] = []
    for _prompt_id, entry in history.items():
        if not isinstance(entry, dict):
            continue
        for node_id, node_out in entry.get("outputs", {}).items():
            if not isinstance(node_out, dict):
                continue
            # ComfyUI may use different keys depending on the output node type
            for key in ("images", "gifs", "videos", "audio"):
                for item in node_out.get(key, []):
                    if isinstance(item, dict) and "filename" in item:
                        files.append({**item, "node_id": str(node_id)})
    return files


def _resolve_output_path(
    filename: str,
    subfolder: str = "",
    image_type: str = "output",
    fallback_dir: "Path | None" = None,
) -> Path:
    """Return the authoritative on-disk path for a ComfyUI output file.

    Files are **never copied**.  Resolution order:

    1. ComfyUI's configured ``--output-directory`` (queried via ``/system_stats``).
       If the file exists there it is returned as-is so that ``collected_paths``
       always reflects the real server location.
    2. Falls back to downloading via ``/view`` into *fallback_dir* when supplied
       (taken from ``output_nodes[].output_path`` in the brainbriefing), or into
       the agent's ``output_dir`` (from settings.json) as a last resort.

    This means ``OUTPUT_PATHS`` in the compressed summary are always real,
    accessible paths that the next session can pass directly to
    ``upload_image()``.
    """
    # --- try the ComfyUI output dir on disk ------------------------------------
    comfy_out = _get_comfyui_output_dir()
    if comfy_out is not None:
        src = comfy_out / subfolder / filename if subfolder else comfy_out / filename
        if src.exists():
            logger.info("executor: output located at %s (%d bytes)", src, src.stat().st_size)
            return src
        logger.debug(
            "executor: %s not found in ComfyUI output dir, falling back to /view", src
        )

    # --- fallback: download via /view to local output_dir ---------------------
    from src.utils.comfyui_client import get_client

    if fallback_dir is None:
        fallback_dir = _output_dir()
    fallback_dir.mkdir(parents=True, exist_ok=True)
    dest = fallback_dir / filename

    params: dict = {"filename": filename, "type": image_type}
    if subfolder:
        params["subfolder"] = subfolder

    client = get_client()
    resp = client.get("/view", params=params, raw=True)
    image_bytes: bytes = resp.content  # type: ignore[attr-defined]
    dest.write_bytes(image_bytes)
    logger.info("executor: downloaded output → %s (%d bytes)", dest, len(image_bytes))
    return dest


# ---------------------------------------------------------------------------
# Shared post-processing helper
# ---------------------------------------------------------------------------

async def _process_completed_job(
    history: dict,
    prompt_id: str,
    brainbriefing: dict,
    *,
    workflow_path: str = "",
    user_message: str = "",
    verbose: bool,
    collected_paths: list[str] | None,
    label: str = "",
) -> AsyncGenerator[str, None]:
    """Download outputs and collect their on-disk paths for one finished job.

    Yields one-line status strings.  ``label`` is an optional prefix like
    ``"[2/5] "`` used in batch runs so the user knows which iteration each
    message belongs to. QA is no longer performed here — the caller returns the
    output images to the model, which inspects them directly.
    """
    pfx = label  # e.g. "[2/5] " or ""

    output_files = _extract_output_files(history)
    if not output_files:
        yield f"{pfx}⚠️ No output files found in ComfyUI history."
        logger.warning("executor: no output files in history for prompt_id=%s", prompt_id)
        return

    # Build a node_id → fallback_dir map from the brainbriefing output_nodes so
    # that downloaded outputs land in the task-specific directory chosen in the
    # brainbriefing, rather than the generic agent output_dir.
    _bb_output_dirs: dict[str, Path] = {}
    try:
        for on in brainbriefing.get("output_nodes", []):
            if not isinstance(on, dict):
                continue
            nid = str(on.get("node_id", ""))
            op = on.get("output_path", "")
            if nid and op:
                p = Path(op)
                if not p.is_absolute():
                    p = _output_dir() / p
                _bb_output_dirs[nid] = p
    except Exception as exc:
        logger.debug("executor: could not parse output_nodes from brainbriefing — %s", exc)

    # Resolve each output file's authoritative on-disk path (no copying).
    # Each path is appended to ``collected_paths`` immediately so the caller
    # (chainlit) can flush the image to the UI as soon as the "💾 Output:" line
    # is yielded, instead of waiting for the whole batch to finish.
    #
    # Primary resolution (no network call): because apply_brainbriefing sets
    # filename_prefix = output_path (e.g. "W:/.../output/image_generation"),
    # ComfyUI saves files as output_path + "_00001_.png", i.e. at
    # Path(output_path).parent / filename.  We check that location first and
    # only fall back to _resolve_output_path (which hits /system_stats) when
    # the file is not found there.
    saved_paths: list[Path] = []
    for item in output_files:
        filename = item.get("filename", "")
        subfolder = item.get("subfolder", "")
        file_type = item.get("type", "output")
        node_id = item.get("node_id", "")
        if not filename:
            continue
        fallback_dir = _bb_output_dirs.get(node_id)
        try:
            resolved: Path | None = None
            # Primary: derive path directly from the brainbriefing output_path.
            if fallback_dir is not None:
                bb_candidate = fallback_dir.parent / filename
                if bb_candidate.exists():
                    logger.info(
                        "executor: output at brainbriefing path %s (%d bytes)",
                        bb_candidate, bb_candidate.stat().st_size,
                    )
                    resolved = bb_candidate
            # Fallback: query ComfyUI /system_stats or download via /view.
            if resolved is None:
                resolved = _resolve_output_path(filename, subfolder, file_type, fallback_dir=fallback_dir)
            saved_paths.append(resolved)
            if collected_paths is not None:
                collected_paths.append(str(resolved))
            yield f"{pfx}💾 Output: `{resolved}`"
        except Exception as exc:
            yield f"{pfx}⚠️ Could not resolve `{filename}`: {exc}"
            logger.warning("executor: resolve failed for %s — %s", filename, exc)

    if not saved_paths:
        yield f"{pfx}❌ All output downloads failed."
        return

    # Copy the finished workflow to the ComfyUI user directory — run in a
    # background thread so a slow UNC/network share doesn't stall execution.
    if workflow_path:
        import threading as _threading
        _threading.Thread(
            target=_copy_workflow_to_user_dir,
            args=(workflow_path,),
            daemon=True,
            name="copy-workflow-to-user-dir",
        ).start()

    output_summary = ", ".join(f"`{p.name}`" for p in saved_paths)
    yield f"{pfx}✅ Done. Outputs: {output_summary}"
    if verbose:
        print(f"[executor] {pfx}Finished. Outputs: {[str(p) for p in saved_paths]}")


# ---------------------------------------------------------------------------
# Public executor — single workflow
# ---------------------------------------------------------------------------

async def execute_workflow(
    workflow_path: str,
    brainbriefing_json: str,
    *,
    user_message: str = "",
    verbose: bool = True,
    collected_paths: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Submit the validated workflow, poll ComfyUI, and collect outputs.

    This is an ``AsyncGenerator[str, None]`` — each yielded string is a one-line
    status update. The blocking ``execute_workflow`` MCP tool consumes this
    generator and returns the collected outputs to the model.

    Args:
        workflow_path:      Absolute path to the validated workflow JSON.
        brainbriefing_json: The brainbriefing JSON string, used to resolve the
                            output save paths for each output node.
        user_message:       The raw text the user originally sent (unused now;
                            retained for call-site compatibility).
        verbose:            Log progress to stdout when True.
    """
    import uuid

    from src.utils.comfyui_progress import stream_comfyui_job

    try:
        brainbriefing: dict = json.loads(brainbriefing_json)
    except Exception:
        brainbriefing = {}

    # ── 1. Submit ──────────────────────────────────────────────────────────
    yield "🚀 Submitting workflow to ComfyUI…"
    client_id = uuid.uuid4().hex
    try:
        prompt_id = _submit_workflow(workflow_path, client_id=client_id)
    except Exception as exc:
        error_msg = f"❌ ComfyUI submission failed: {exc}"
        logger.error("executor: %s", error_msg)
        yield error_msg
        return

    yield f"✅ Queued · prompt_id=`{prompt_id}` — streaming progress…"
    if verbose:
        print(f"[executor] Queued prompt_id={prompt_id}")

    # ── 2. Stream progress via WebSocket ───────────────────────────────────
    node_titles = _load_node_titles(workflow_path)
    history: dict | None = None
    error_result: dict | None = None
    _gen = stream_comfyui_job(prompt_id, client_id, node_titles=node_titles)
    try:
        async for event in _gen:
            if isinstance(event, dict):
                if "history" in event:
                    history = event["history"]
                else:
                    error_result = event
                break
            yield event
    finally:
        await _gen.aclose()

    if error_result is not None:
        error_msg = f"❌ ComfyUI execution error: {error_result.get('error')}"
        logger.error("executor: %s", error_msg)
        yield error_msg
        return

    if history is None:
        yield "❌ ComfyUI stream ended without a result."
        return

    yield "✅ ComfyUI execution complete — collecting outputs…"

    # ── 3. Download + collect outputs ──────────────────────────────────────
    async for line in _process_completed_job(
        history,
        prompt_id,
        brainbriefing,
        workflow_path=workflow_path,
        user_message=user_message,
        verbose=verbose,
        collected_paths=collected_paths,
    ):
        yield line


# ---------------------------------------------------------------------------
# Public executor — batch (submit-all-then-poll)
# ---------------------------------------------------------------------------

async def execute_workflows_batch(
    workflow_paths: list[str],
    brainbriefing_json: str,
    *,
    user_message: str = "",
    verbose: bool = True,
    collected_paths: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Submit ALL workflows to ComfyUI first, then poll + process each in order.

    This avoids the submit→wait→submit→wait pattern: ComfyUI receives the full
    batch immediately and can start executing jobs while the client is still
    submitting remaining ones.  Polling then starts *after* the last submission,
    so earlier jobs are frequently already done by the time we reach them.

    Args:
        workflow_paths:     Ordered list of absolute workflow JSON file paths.
        brainbriefing_json: The brainbriefing JSON string (for output save paths).
        user_message:       Unused; retained for call-site compatibility.
        verbose:            Log progress to stdout when True.
    """
    import uuid

    from src.utils.comfyui_progress import stream_comfyui_job

    try:
        brainbriefing: dict = json.loads(brainbriefing_json)
    except Exception:
        brainbriefing = {}

    total = len(workflow_paths)

    # ── Phase 1: submit all ────────────────────────────────────────────────
    # One client_id per prompt so each WebSocket subscription only receives
    # events for its own job.
    queued: list[tuple[str, str, str]] = []  # [(prompt_id, workflow_path, client_id), ...]
    for idx, wf_path in enumerate(workflow_paths, 1):
        yield f"🚀 Queuing iteration {idx}/{total}…"
        cid = uuid.uuid4().hex
        try:
            prompt_id = _submit_workflow(wf_path, client_id=cid)
            queued.append((prompt_id, wf_path, cid))
            yield f"✅ Iteration {idx}/{total} queued · prompt_id=`{prompt_id}`"
            if verbose:
                print(f"[executor] Batch {idx}/{total} queued prompt_id={prompt_id}")
        except Exception as exc:
            error_msg = f"❌ Submission failed for iteration {idx}/{total}: {exc}"
            logger.error("executor: %s", error_msg)
            yield error_msg

    if not queued:
        yield "❌ All workflow submissions failed — nothing to poll."
        return

    yield (
        f"⏳ All {len(queued)}/{total} workflows queued — "
        f"streaming progress in submission order…"
    )

    # ── Phase 2: stream progress + process each in submission order ────────
    for idx, (prompt_id, _wf_path, cid) in enumerate(queued, 1):
        label = f"[{idx}/{len(queued)}] "
        yield f"{label}⏳ Streaming progress (prompt_id=`{prompt_id}`)…"
        if verbose:
            print(f"[executor] Batch streaming {idx}/{len(queued)} prompt_id={prompt_id}")

        history: dict | None = None
        error_result: dict | None = None
        _node_titles = _load_node_titles(_wf_path)
        _gen = stream_comfyui_job(prompt_id, cid, node_titles=_node_titles)
        try:
            async for event in _gen:
                if isinstance(event, dict):
                    if "history" in event:
                        history = event["history"]
                    else:
                        error_result = event
                    break
                yield f"{label}{event}"
        finally:
            await _gen.aclose()

        if error_result is not None:
            error_msg = f"{label}❌ ComfyUI execution error: {error_result.get('error')}"
            logger.error("executor: %s", error_msg)
            yield error_msg
            continue  # move on to the next iteration, don't abort the whole batch

        if history is None:
            yield f"{label}❌ ComfyUI stream ended without a result."
            continue

        yield f"{label}✅ Complete — collecting outputs…"

        async for line in _process_completed_job(
            history,
            prompt_id,
            brainbriefing,
            workflow_path=_wf_path,
            user_message=user_message,
            verbose=verbose,
            collected_paths=collected_paths,
            label=label,
        ):
            yield line
