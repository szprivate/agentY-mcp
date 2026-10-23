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

def _cost_gate(paths: list[str], confirm: bool) -> list | None:
    """Pre-flight for paid (partner) nodes: None to go ahead, else the refusal as the
    tool answer (``error_kind`` confirm_cost / insufficient_credits). With *confirm*
    the go-ahead is remembered for the files so the submission does not ask again."""
    import json
    from agenty_core import partner_credits as pc
    try:
        est = pc.preflight_many([str(p) for p in paths], confirm=confirm)
    except pc.CostGateError as gate:
        return [json.dumps(gate.payload())]
    except Exception:  # noqa: BLE001 - a failed check never stops a render
        return None
    if confirm and est.get("paid"):
        for p in paths:
            pc.confirm_path(str(p), float("inf"))
    return None


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
async def execute_workflow(workflow_path: str, brainbriefing_json: str = "", confirm_cost: bool = False) -> list:
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
        confirm_cost:       True only once the user has agreed to the estimated cost.
                            Paid (partner) nodes show their price first; at or above
                            the confirmation level (default $1) the call answers
                            ``error_kind: confirm_cost`` with the estimate - tell the
                            user, ask, and repeat with ``confirm_cost=True`` after a
                            yes. ``insufficient_credits``: the balance can't cover it.
        brainbriefing_json: Optional brainbriefing JSON string. When provided, its
                            ``output_nodes[].output_path`` entries are used to
                            resolve where each output was saved.

    Returns:
        A text summary (status lines + output file paths) followed by the output
        image content for direct visual QA.
    """
    import asyncio
    refusal = await asyncio.to_thread(_cost_gate, [workflow_path], confirm_cost)
    if refusal:
        return refusal
    collected: list[str] = []
    log: list[str] = []
    async for line in _stream_one(
        workflow_path, brainbriefing_json, verbose=False, collected_paths=collected
    ):
        if isinstance(line, str):
            log.append(line)
    return _build_result(log, collected)


@tool
async def execute_workflows_batch(workflow_paths: list, brainbriefing_json: str = "",
                                  confirm_cost: bool = False) -> list:
    """Run several validated workflows (a batch) on ComfyUI and return their outputs.

    Use this for batch / variation runs — e.g. the per-variation workflow copies
    produced by ``duplicate_workflow``. All workflows are submitted up front, then
    polled in order, so ComfyUI can start working the queue immediately.

    Args:
        workflow_paths:     Ordered list of validated workflow JSON file paths.
        brainbriefing_json: Optional brainbriefing JSON string (for output paths).
        confirm_cost:       True only once the user has agreed to the estimated cost
                            (the batch is judged on the SUM of its paid nodes; see
                            ``execute_workflow``).

    Returns:
        A text summary (per-iteration status + output file paths) followed by the
        output image content for direct visual QA.
    """
    import asyncio
    paths = [str(p) for p in (workflow_paths or [])]
    refusal = await asyncio.to_thread(_cost_gate, paths, confirm_cost)   # judged on the sum
    if refusal:
        return refusal
    collected: list[str] = []
    log: list[str] = []
    async for line in _stream_batch(
        paths, brainbriefing_json, verbose=False, collected_paths=collected
    ):
        if isinstance(line, str):
            log.append(line)
    return _build_result(log, collected)


@tool
async def partner_run(node_type: str, inputs: dict | None = None, settings: dict | None = None,
                      save: str = "auto", name: str = "", run: bool = True,
                      confirm_cost: bool = False) -> list:
    """Build and run ONE partner (API) node directly - no template search.

    The preferred route when the request names a partner model or node: Seedance,
    Kling, GPT Image, Nano Banana / Gemini image, Ideogram, Meshy, Veo, Runway ...
    The node's own schema decides the inputs; files get loaders wired to the right
    slots, the result gets a save node, the graph is validated and (``run=True``)
    executed - the same path as ``execute_workflow``, so the outputs come back as
    images / sampled frames to look at.

    ``node_type`` is the class name or the name you know it by ("Seedance 2.5 first
    last frame"); an ambiguous name returns candidates and builds nothing.
    ``inputs`` maps FILE slots to a path (or a list of paths for a slot group, e.g.
    ``{"model.reference_images": ["a.png", "b.png"]}`` fills image_1, image_2 ...).
    ``settings`` maps everything else: ``prompt``, ``model`` (a dynamic combo whose
    option decides the other settings), ``resolution``, ``duration``,
    ``generate_audio`` ... A bare name works when unambiguous. A value the node does
    not offer is an error listing the options; nothing is changed silently.
    ``save``: "image", "video" or "auto". ``run=False`` only builds and validates.

    Runs on the user's partner credits: once per request, never to test. The price
    shows before it runs (``estimate_usd``; ``run=False`` returns it without
    running). At or above the confirmation level (default $1) the run is refused with
    ``error_kind: confirm_cost`` - tell the user the estimate, ask, and call again
    with ``confirm_cost=True`` only after a yes. ``insufficient_credits``: even the
    lowest estimate is above the balance. A finished run reports ``partner_cost_usd``.

    Args:
        node_type: Node class name or display name.
        inputs: ``{slot: file path | [paths]}`` for image / video / audio inputs.
        settings: ``{name: value}`` for prompt and every widget.
        save: "image", "video" or "auto".
        name: Short name for the output files.
        run: False to build and validate only.
        confirm_cost: True only once the user has agreed to the estimated cost.
    """
    import asyncio
    import json
    from agenty_core.tools.partner_run import prepare_partner_workflow
    from src.tools.execution import _cost_gate  # noqa: F401  (same module; kept explicit)

    prepared = await asyncio.to_thread(prepare_partner_workflow, node_type, inputs, settings, save, name)
    if prepared.get("status") == "ready":
        try:
            from agenty_core import partner_credits as _pc
            _est = await asyncio.to_thread(
                _pc.estimate_workflow, json.loads(Path(prepared["workflow_path"]).read_text(encoding="utf-8")))
            if _est["paid"]:
                prepared["estimate_usd"] = {"min": _est["min_usd"], "max": _est["max_usd"],
                                            "unknown_nodes": _est["unknown"]}
        except Exception:  # noqa: BLE001 - an estimate never stops a build
            pass
    if prepared.get("status") != "ready" or not run:
        return [json.dumps(prepared if prepared.get("status") != "ready" else {**prepared, "ran": False})]
    refusal = await asyncio.to_thread(_cost_gate, [prepared["workflow_path"]], confirm_cost)
    if refusal:
        return [json.dumps({**prepared, **json.loads(refusal[0]), "ran": False})]
    collected: list[str] = []
    log: list[str] = [f"Built {prepared.get('node')} -> {prepared['workflow_path']}"
                      + "".join(f"\nwarning: {w}" for w in prepared.get("warnings") or [])]
    async for line in _stream_one(prepared["workflow_path"], "", verbose=False, collected_paths=collected):
        if isinstance(line, str):
            log.append(line)
    return _build_result(log, collected)


@tool
async def run_variants(workflow_path: str, variants: list, run: bool = True,
                       confirm_cost: bool = False) -> list:
    """Make and run N independent variants of ONE workflow in a single call.

    For "give me 4 versions", "try three lightings", "the same shot for each of these
    prompts / seeds / images": ONE call duplicates the workflow N times (fresh seeds),
    patches each copy with its own overrides, validates them and - with ``run=True`` -
    submits them ALL up front (like ``execute_workflows_batch``) and returns the
    outputs, instead of duplicate_workflow -> update_workflow -> execute_workflow once
    per variant.

    ``variants`` is a list of objects, e.g.
    ``[{"label": "warm", "set": {"6.text": "a warm lamp"}},
      {"label": "cold", "set": {"6.text": "a cold lamp", "12.image": "b.png"}}]``.
    ``set`` keys are ``<node id>.<input name>``; the full ``update_workflow`` shape
    (``patches`` / ``add_nodes`` / ``remove_nodes``) works too; ``{}`` is a
    fresh-seeded copy. Up to 24. A variant that fails validation is reported and
    skipped; the rest run. ``run=False`` only builds and validates.

    Args:
        workflow_path: Path of the validated base workflow.
        variants: List of variant objects.
        run: False to build and validate only.
        confirm_cost: True only once the user has agreed to the estimated cost. The
            variants' paid prices are added up; at or above the confirmation level
            (default $1) the call answers ``error_kind: confirm_cost`` until a yes.
    """
    import asyncio
    import json
    from agenty_core.tools.variants import prepare_variants

    prepared = await asyncio.to_thread(prepare_variants, workflow_path, variants)
    ready = list(prepared.get("ready") or [])
    if prepared.get("status") == "error" or not run or not ready:
        return [json.dumps({**prepared, "ran": False})]
    refusal = await asyncio.to_thread(_cost_gate, ready, confirm_cost)
    if refusal:
        return [json.dumps({**prepared, **json.loads(refusal[0]), "ran": False})]
    collected: list[str] = []
    log: list[str] = [json.dumps({"variants": [{k: v for k, v in x.items() if k != "problems" or v}
                                                for x in prepared["variants"]]})]
    async for line in _stream_batch(ready, "", verbose=False, collected_paths=collected):
        if isinstance(line, str):
            log.append(line)
    return _build_result(log, collected)
