"""
ComfyUI tools for the Strands agent.

Exports tool lists for the Researcher, Brain, Info, Triage, Planner,
Learnings, ErrorChecker, and VisionAgent agents.
"""

from src.tools.comfyui import (  # noqa: F401
    # Execution control
    interrupt_execution,
    free_memory,
    # Queue
    queue,
    # History
    get_history,
    get_prompt_status_by_id,
    clear_history,
    # Diagnostics
    get_logs,
    get_system_stats,
    get_comfyui_dirs,
    # Prompt submission
    submit_prompt,
    # Workflow handoff (replaces submit_prompt for the Brain)
    signal_workflow_ready,
    # Batch: create iteration copies of a validated workflow
    duplicate_workflow,
    # Node inspection
    get_node_schema,
    get_workflow_node_info,
    search_nodes,
    # Workflow templates
    get_workflow_catalog,
    get_workflow_template,
    # Workflow modification
    save_workflow,
    patch_workflow,
    add_workflow_node,
    remove_workflow_node,
    update_workflow,
    replace_node,
    apply_brainbriefing,
    # Workflow validation
    validate_workflow,
    # Public helpers
    reset_patch_workflow_guard,
    # Session cache management
    clear_tool_caches,
)
from src.tools.image_handling import (  # noqa: F401
    upload_image,
    view_image,
    get_image_resolution,
    analyze_image,
    download_image,
)
from src.tools.comfyui import check_model  # noqa: F401
from src.tools.huggingface import (  # noqa: F401
    search_huggingface_models,
    get_model_info,
    find_hf_file,
    download_hf_model,
)
from src.tools.file_tools import read_text_file, write_text_file  # noqa: F401
from src.tools.iterate import iterate  # noqa: F401
from src.tools.shell import run_script  # noqa: F401
from src.tools.memory_tools import memory_read, memory_write  # noqa: F401
from src.tools.web_search import web_search, web_search_images  # noqa: F401
from strands_tools import file_read  # noqa: F401
from strands_tools import calculator  # noqa: F401
from strands_tools import stop  # noqa: F401

# ---------------------------------------------------------------------------
# Info-agent tools – read-only; answers questions about capabilities/models/workflows.
# ---------------------------------------------------------------------------
INFO_TOOLS: list = [
    memory_read,
    get_workflow_catalog,
    get_workflow_template,
    check_model,
    get_node_schema,
    search_nodes,
    read_text_file,
    file_read,
    stop,
    analyze_image,
    get_image_resolution,
    # Web search
    web_search,
    web_search_images,
    download_image,   # fetch a found reference image to disk
]

# ---------------------------------------------------------------------------
# Story-agent tools – pure text generation; no tools needed.
# The story agent writes small storylines and calls no ComfyUI tools.
# ---------------------------------------------------------------------------
STORY_TOOLS: list = []

# ---------------------------------------------------------------------------
# Researcher tools – template lookup, asset upload, model resolution.
# ---------------------------------------------------------------------------
RESEARCHER_TOOLS: list = [
    get_workflow_catalog,
    get_workflow_template,
    check_model,         # verify model files exist in the ComfyUI installation
    get_comfyui_dirs,
    read_text_file,
    get_image_resolution,
    analyze_image,
    upload_image,  # needed to stage prior-session outputs as new inputs
    download_image,  # fetch a web reference image to disk, then stage via upload_image
    run_script,  # needed for skills (e.g. image-downsize)
    # Web search
    web_search,
    web_search_images,
    iterate,
    calculator,
    memory_read,
    memory_write,
    # HuggingFace – discover and download missing models
    search_huggingface_models,
    get_model_info,
    find_hf_file,       # locate a file by name across HF (API + DDG fallback)
    download_hf_model,
    stop,
]

# ---------------------------------------------------------------------------
# Brain tools – workflow assembly only (steps 1-5 + handoff).
# Execution, polling, and Vision QA are handled by the Executor.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Triage tools – stateless intent classifier; no tools needed.
# ---------------------------------------------------------------------------
TRIAGE_TOOLS: list = []

# ---------------------------------------------------------------------------
# Planner tools – stateless multi-step decomposer; no tools needed.
# ---------------------------------------------------------------------------
PLANNER_TOOLS: list = []

# ---------------------------------------------------------------------------
# Vision Agent tools – stateless, single-shot vision analyser.
# Makes direct Ollama API calls; no Strands tools required.
# ---------------------------------------------------------------------------
VISION_AGENT_TOOLS: list = []

# ---------------------------------------------------------------------------
# Learnings tools – stateless pattern-analyser; no tools needed.
# ---------------------------------------------------------------------------
LEARNINGS_TOOLS: list = []

# ---------------------------------------------------------------------------
# Error-checker tools – diagnostics only; no workflow modification.
# ---------------------------------------------------------------------------
ERROR_CHECKER_TOOLS: list = [
    get_logs,
    get_system_stats,
]

BRAIN_TOOLS: list = [
    # Node inspection (schema lookup only – no model checking)
    get_node_schema,
    get_workflow_node_info,
    # Server directories (resolve authoritative output path)
    get_comfyui_dirs,
    # Upload input images
    upload_image,
    get_image_resolution,
    # Workflow assembly, modification & validation
    get_workflow_template,
    apply_brainbriefing,
    update_workflow,
    replace_node,
    save_workflow,
    search_nodes,
    check_model,
    # Handoff to executor (replaces submit_prompt)
    signal_workflow_ready,
    # Batch: duplicate workflow for each iteration
    duplicate_workflow,
    # Script execution (for skills, e.g. image-downsize)
    run_script,
    # Iteration utility
    iterate,
    # File operations (strands built-in + project)
    file_read,
    read_text_file,
    write_text_file,
    # Long-term memory (local FAISS + nomic-embed-text)
    memory_read,
    memory_write,
    stop,
]
