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

from mcp.server.fastmcp import FastMCP

from src import tools as T

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
"""

mcp = FastMCP("agentY", instructions=INSTRUCTIONS)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------
# All tools are plain functions (see src/tools/*). They are registered here with
# structured_output disabled so each returns content blocks (text + images)
# verbatim, matching their original behaviour.

_TOOLS = [
    # ── Workflow templates & catalog ──────────────────────────────────────
    T.get_workflow_catalog,
    T.get_workflow_template,
    # ── Node inspection ───────────────────────────────────────────────────
    T.get_node_schema,
    T.get_workflow_node_info,
    T.search_nodes,
    # ── Workflow assembly / modification ──────────────────────────────────
    T.save_workflow,
    T.patch_workflow,
    T.update_workflow,
    T.add_workflow_node,
    T.remove_workflow_node,
    T.replace_node,
    T.apply_brainbriefing,
    T.duplicate_workflow,
    # ── Template registry (add / remove custom templates) ─────────────────
    T.register_workflow_template,
    T.unregister_workflow_template,
    # ── Validation ────────────────────────────────────────────────────────
    T.validate_workflow,
    # ── Execution ─────────────────────────────────────────────────────────
    T.execute_workflow,
    T.execute_workflows_batch,
    # ── Headless batch jobs (detached worker, pollable status) ────────────
    T.start_batch_job,
    T.get_batch_status,
    T.stop_batch_job,
    T.list_batch_jobs,
    T.submit_prompt,
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
    T.view_image,
    T.get_image_resolution,
    T.analyze_image,
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
]

for _fn in _TOOLS:
    # structured_output=False → return text/image content blocks verbatim
    # (these tools return JSON strings or image content, not typed models).
    mcp.add_tool(_fn, structured_output=False)


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
