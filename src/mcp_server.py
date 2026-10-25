"""agentY MCP server.

Exposes the ComfyUI workflow toolkit (assembly, validation, execution),
HuggingFace model management, image handling, web search, file I/O, and
long-term memory as Model Context Protocol tools over stdio.

The MCP host (e.g. Claude Desktop) is the orchestrator: it loads the agentY
Skills (procedural knowledge) and calls these tools. There is no in-process LLM
and no Ollama — the host supplies the model.

Run with:
    python -m src
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _load_env() -> list[str]:
    """Load .env files into os.environ at startup (explicit env always wins).

    Order: this repo's own ``.env``, then agentY's ``.env`` - from
    ``AGENTY_ENV_FILE`` (a file) or ``AGENTY_HOME`` (agentY's folder), else the
    sibling checkout ``../agentY/.env``; then ``$CLAUDE_PLUGIN_DATA/.env`` and ``~/.agenty/.env``. ``override=False`` throughout, so a
    variable set by the MCP host (or an earlier file) is never replaced.
    """
    import os

    from dotenv import load_dotenv

    root = Path(__file__).resolve().parent.parent
    candidates = [root / ".env"]
    if os.environ.get("AGENTY_ENV_FILE"):
        candidates.append(Path(os.environ["AGENTY_ENV_FILE"]).expanduser())
    elif os.environ.get("AGENTY_HOME"):
        candidates.append(Path(os.environ["AGENTY_HOME"]).expanduser() / ".env")
    else:
        candidates.append(root.parent / "agentY" / ".env")
    # Plugin installed from GitHub (no sibling agentY): the plugin's data folder (survives
    # plugin updates) or ~/.agenty hold the keys.
    if os.environ.get("CLAUDE_PLUGIN_DATA"):
        candidates.append(Path(os.environ["CLAUDE_PLUGIN_DATA"]) / ".env")
    candidates.append(Path.home() / ".agenty" / ".env")
    loaded = []
    for f in candidates:
        if f.is_file() and load_dotenv(f, override=False):
            loaded.append(str(f))
    return loaded


_ENV_FILES = _load_env()

# Anchor the shared agenty_core tool layer on this repo's root (it now lives in
# a sibling package, so it can't resolve config/ and output_workflows/ from its
# own __file__). Must run before the tool modules are imported below.
from agenty_core import set_project_root

set_project_root(Path(__file__).resolve().parent.parent)

from src import tools as T
from src import skills_mcp

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("agentY.mcp")

INSTRUCTIONS = """\
agentY turns natural-language requests into ComfyUI image/video workflows.

Typical flow (see the agentY Skills for full procedures):
  1. Pick a template with get_workflow_catalog / get_workflow_template, or build
     from scratch when none fits.
  2. Resolve models with check_model; download missing ones from HuggingFace.
  3. Assemble: apply a brainbriefing (apply_brainbriefing) or patch nodes
     (update_workflow / replace_node), then validate_workflow.
  4. execute_workflow (or execute_workflows_batch for variations) — it returns
     the generated image(s) so you can QA them directly against the request.

When the user points at their open ComfyUI canvas ("this node", "the prompt I
have selected"), read it with get_canvas_selection and write changes back with
set_canvas_node_params — do not guess from a workflow file on disk.

Skills: agentY keeps its know-how (assembly, prompting per model family, partner
nodes, upscaling, Atlas/3D, DCC, Deadline, storyboards ...) in skills. BEFORE a
task, call list_skills and, when one matches, read_skill(name) and follow it.
Claude Code loads the same skills itself; other clients get them through these
two tools (and as MCP prompts).
"""

mcp = FastMCP("agentY", instructions=INSTRUCTIONS)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------
# All tools are plain functions (see src/tools/*). They are registered here with
# structured_output disabled so each returns content blocks (text + images)
# verbatim, matching their original behaviour.

_TOOLS = [
    # ── Skills, for clients that cannot load them themselves ───────────────
    skills_mcp.list_skills,
    skills_mcp.read_skill,
    # ── Talk to a RUNNING agentY host (its own orchestrator/skills/hooks) ──
    T.agenty_turn,
    T.agenty_turn_status,
    T.agenty_conversations,
    T.agenty_reply,
    T.agenty_stop,
    # ── Workflow templates & catalog ──────────────────────────────────────
    T.get_workflow_catalog,
    T.get_workflow_template,
    # ── Workflow recipes (task -> model -> node clusters knowledge base) ──
    T.list_workflow_recipes,
    T.get_workflow_recipe,
    # ── Node inspection ───────────────────────────────────────────────────
    T.get_node_schema,
    T.get_workflow_node_info,
    T.search_nodes,
    # ── Workflow assembly / modification ──────────────────────────────────
    T.save_workflow,
    T.open_workflow_in_canvas,
    T.patch_workflow,
    T.update_workflow,
    T.add_workflow_node,
    T.remove_workflow_node,
    T.replace_node,
    T.apply_brainbriefing,
    T.assemble_workflow_deterministic,
    T.duplicate_workflow,
    # ── Template registry (add / remove custom templates) ─────────────────
    T.register_workflow_template,
    T.unregister_workflow_template,
    # ── Live canvas (what the user has selected in the open ComfyUI page) ──
    T.get_canvas_selection,
    T.set_canvas_node_params,
    # ── Validation ────────────────────────────────────────────────────────
    T.validate_workflow,
    # ── Execution ─────────────────────────────────────────────────────────
    T.execute_workflow,
    T.execute_workflows_batch,
    # ── One partner (API) node built from its schema and run directly ─────
    T.partner_run,
    # ── N independent variants of one workflow, duplicated + patched + queued together ──
    T.run_variants,
    # ── Headless batch jobs (detached worker, pollable status) ────────────
    T.start_batch_job,
    T.get_batch_status,
    T.stop_batch_job,
    T.list_batch_jobs,
    T.submit_prompt,
    T.estimate_workflow_cost,
    T.queue,
    T.get_history,
    T.get_prompt_status_by_id,
    T.clear_history,
    T.interrupt_execution,
    T.free_memory,
    # ── Server / diagnostics ──────────────────────────────────────────────
    T.get_comfyui_dirs,
    T.get_system_stats,
    T.get_logs,
    T.check_model,
    # ── Image handling ────────────────────────────────────────────────────
    T.upload_image,
    T.download_image,
    T.upload_file_to_url,
    T.view_image,
    T.get_image_resolution,
    T.analyze_image,
    # ── Generation on the user's own DashScope key ────────────────────────
    T.dashscope_generate,
    T.dashscope_fetch,
    # ── Show files in the bEpic viewer (focus, Edit panel) ────────────────
    T.show_in_viewer,
    T.render_camera_move,
    # ── Editable motion graphics (a *.mgscene.json scene, rendered by Remotion) ──
    T.mg_scene_validate,
    T.mg_scene_preview_frame,
    T.mg_render,
    # ── World Labs Atlas: picture / prompt -> 3D scene mesh (WORLDLABS_API_KEY) ──
    T.atlas_create_world,
    T.atlas_expand_world,
    T.atlas_rebuild_world_mesh,
    T.atlas_splat_to_mesh,
    T.atlas_fetch,
    T.atlas_list,
    T.atlas_render_view,
    T.atlas_open_in_viewer,
    T.atlas_capture_around,
    T.train_splat,
    T.splat_training_status,
    # ── World Labs Marble: a ready splat world from pictures, SPZ / PLY export (WLT_MARBLE_API_KEY) ──
    T.marble_create_world,
    T.marble_export,
    # ── LoRA training: dataset, the user's review gate, local / hosted trainers ──
    T.lora_dataset_prepare,
    T.lora_dataset_set_captions,
    T.lora_dataset_review,
    T.train_lora,
    T.lora_training_status,
    T.lora_training_stop,
    # ── Model from a reference photo in Blender / Maya / Houdini ──
    T.dcc_build,
    T.dcc_silhouette_check,
    T.find_app_installs,
    T.measure_reference,
    # ── Ayon pipeline (session launched through Ayon; AYON_API_KEY / AYON_SERVER_URL optional) ──
    T.ayon_context,
    T.ayon_load,
    T.ayon_mark_publish,
    T.ayon_publish,
    T.ayon_open_tool,
    # ── Deadline render farm (DEADLINE_* settings, all optional) ──
    T.submit_to_deadline,
    T.deadline_job_status,
    T.deadline_farm_info,
    # ── Execution modes: where open-weight models run (local / hybrid / Comfy Cloud) ──
    T.set_execution_mode_for_turn,
    T.get_execution_mode,
    # ── HuggingFace model management ──────────────────────────────────────
    T.search_huggingface_models,
    T.get_model_info,
    T.find_hf_file,
    T.download_hf_model,
    # ── Web search ────────────────────────────────────────────────────────
    T.web_search,
    T.web_search_images,
    # ── File I/O, shell, memory ───────────────────────────────────────────
    T.read_text_file,
    T.write_text_file,
    T.run_script,
    T.memory_read,
    T.memory_write,
    # Per-project facts, shared with the agentY panel through ComfyUI's user dir.
    T.project_memory_read,
    T.project_memory_write,
    T.project_memory_forget,
]

# Further core tools, imported one by one so a missing/broken one never stops the
# server from starting. (reverse_image_search arrives with its agenty_core module.)
import importlib

for _mod, _names in [
    ("agenty_core.tools.comfyui", ["find_custom_node_for", "install_custom_node", "get_agent_output_dirs"]),
    ("agenty_core.tools.huggingface", ["wait_for_download"]),
    ("agenty_core.tools.model_research", ["hf_search", "hf_repo", "hf_file", "find_local_models", "inspect_workflow_file"]),
    ("agenty_core.tools.workspace_tools", ["get_node_source", "list_files", "find_workflows", "media_info", "video_frames", "read_web_page"]),
    ("agenty_core.tools.reverse_search", ["reverse_image_search"]),
]:
    try:
        _m = importlib.import_module(_mod)
        _TOOLS.extend(getattr(_m, _n) for _n in _names)
    except Exception as _e:  # noqa: BLE001
        logger.warning("optional core tools %s not offered: %s", _names, _e)

for _fn in _TOOLS:
    # structured_output=False → return text/image content blocks verbatim
    # (these tools return JSON strings or image content, not typed models).
    mcp.add_tool(_fn, structured_output=False)


try:
    _N_SKILL_PROMPTS = skills_mcp.register_prompts(mcp)
except Exception as _e:  # noqa: BLE001 - prompts are a courtesy; the tools still work
    _N_SKILL_PROMPTS = 0
    logger.warning("skills not offered as prompts: %s", _e)


def main() -> None:
    """Run the agentY MCP server over stdio.

    The JSON-RPC protocol owns the process stdout. Many tool/util modules print
    diagnostics to stdout, which would corrupt that stream, so we hand the real
    stdout to the transport and redirect Python-level stdout to stderr.
    """
    import anyio
    from io import TextIOWrapper
    from mcp.server.stdio import stdio_server

    real_stdout = sys.stdout
    sys.stdout = sys.stderr  # stray prints now go to stderr

    logger.info("agentY MCP server starting — %d tools registered", len(_TOOLS))

    async def _run() -> None:
        transport_stdout = anyio.wrap_file(TextIOWrapper(real_stdout.buffer, encoding="utf-8"))
        async with stdio_server(stdout=transport_stdout) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )

    anyio.run(_run)


if __name__ == "__main__":
    main()
