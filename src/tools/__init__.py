"""agentY MCP tools.

ComfyUI control, workflow assembly/validation, HuggingFace model management,
image handling, web search, file I/O, shell, and long-term memory.

These were originally Strands ``@tool`` functions for a multi-agent pipeline.
They are now plain functions registered with FastMCP in ``src/mcp_server.py``;
the single MCP host (Claude Desktop) is the orchestrator, so there are no longer
per-agent tool subsets.
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
    # Models
    check_model,
    # Session cache management (called at server startup)
    clear_tool_caches,
    reset_patch_workflow_guard,
)
from src.tools.image_handling import (  # noqa: F401
    upload_image,
    view_image,
    get_image_resolution,
    analyze_image,
    download_image,
)
from src.tools.huggingface import (  # noqa: F401
    search_huggingface_models,
    get_model_info,
    find_hf_file,
    download_hf_model,
)
from src.tools.file_tools import read_text_file, write_text_file  # noqa: F401
from src.tools.shell import run_script  # noqa: F401
from src.tools.memory_tools import memory_read, memory_write  # noqa: F401
from src.tools.web_search import web_search, web_search_images  # noqa: F401
from src.tools.execution import execute_workflow, execute_workflows_batch  # noqa: F401
from src.tools.batch import (  # noqa: F401
    start_batch_job,
    get_batch_status,
    stop_batch_job,
    list_batch_jobs,
)
from src.tools.workflow_registry import (  # noqa: F401
    register_workflow_template,
    unregister_workflow_template,
)
