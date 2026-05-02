"""Brain steering handlers for agentY.

Two handlers enforce Brain-specific guardrails just-in-time:

Handler 1 — ForbiddenToolHandler (rule-based, no LLM)
    Blocks save_workflow calls that are not for new-workflow builds.
    Note: submit_prompt, view_image, and analyze_image are NOT registered in
    BRAIN_TOOLS, so those are already blocked at the tool-registration layer.
    This handler guards save_workflow, which IS registered but should only
    be used when the Brain is building a workflow from scratch, not patching.

Handler 2 — ModelSamplingFluxHandler (rule-based, no LLM)
    Pre-validation: before an update_workflow call, loads the workflow file
    and checks whether it contains any ModelSamplingFlux node.  If so, and if
    the call's patches are missing any of the four required inputs
    (max_shift, base_shift, width, height), the handler automatically injects
    the missing patches with sensible defaults and returns Proceed.

    This eliminates the retry cycle where the agent had to call
    update_workflow, receive a validation error, load the flux-sampling skill,
    and retry — saving ~5 333 tokens per session on affected workflows.

    NODE_VALIDATION_RULES maps class_type → required inputs + defaults.
    Add new entries there to extend coverage to other node types with known
    deterministic validation requirements.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from strands import Agent
from strands.types.tools import ToolUse
from strands.vended_plugins.steering import (
    Guide,
    Proceed,
    SteeringHandler,
    ToolSteeringAction,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-validation rules for nodes with deterministic required inputs
# ---------------------------------------------------------------------------
# Each entry:
#   'required_inputs' – frozenset of input names that must be present
#   'defaults'        – fallback values used when auto-injecting missing patches
#
# Add new entries here when a new node type shows consistent validation
# failures in production logs.  No other code changes are needed.

NODE_VALIDATION_RULES: dict[str, dict] = {
    "ModelSamplingFlux": {
        "required_inputs": frozenset({"max_shift", "base_shift", "width", "height"}),
        "defaults": {
            "max_shift": 1.15,
            "base_shift": 0.5,
            "width": 1024,
            "height": 1024,
        },
    },
    # Example — add entries like this for future node types:
    # "SomeOtherNode": {
    #     "required_inputs": frozenset({"param1", "param2"}),
    #     "defaults": {"param1": 0, "param2": 512},
    # },
}

# ---------------------------------------------------------------------------
# Handler 1: Forbidden tool guard (rule-based)
# ---------------------------------------------------------------------------

_FORBIDDEN_TOOLS = frozenset(["save_workflow"])
_FORBIDDEN_REASON = (
    "save_workflow is reserved for building entirely new workflows from scratch. "
    "You are patching an existing template — use update_workflow() instead. "
    "Call update_workflow(workflow_path, patches, add_nodes, remove_nodes)."
)


class BrainForbiddenToolHandler(SteeringHandler):
    """Blocks save_workflow when the Brain is patching a template.

    submit_prompt, view_image, and analyze_image are not registered in
    BRAIN_TOOLS, so this handler only needs to guard save_workflow.
    """

    name: str = "brain_forbidden_tool"

    async def steer_before_tool(
        self, *, agent: Agent, tool_use: ToolUse, **kwargs: Any
    ) -> ToolSteeringAction:
        tool_name = tool_use.get("name", "")
        if tool_name in _FORBIDDEN_TOOLS:
            logger.debug("brain_forbidden_tool: blocking %s", tool_name)
            return Guide(reason=_FORBIDDEN_REASON)
        return Proceed(reason="tool allowed")


# ---------------------------------------------------------------------------
# Handler 2: Pre-validation patch injector (rule-based, no LLM)
# ---------------------------------------------------------------------------


def _parse_json_arg(val: Any) -> list:
    """Parse a tool argument that may be a JSON string or already a list."""
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return val if isinstance(val, list) else []


def _load_workflow_for_prevalidation(workflow_path: str) -> dict:
    """Load a workflow JSON file from disk.  Returns empty dict on any error."""
    try:
        path = Path(workflow_path)
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _find_nodes_by_class(workflow: dict, class_name: str) -> list[tuple[str, dict]]:
    """Return (node_id, node_dict) pairs for every node whose class_type matches."""
    results = []
    for nid, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == class_name:
            results.append((nid, node))
    return results


def _inject_validation_patches(tool_input: dict, workflow: dict) -> int:
    """Mutate *tool_input* in place, adding any patches required by NODE_VALIDATION_RULES.

    For each rule:
      - Find all matching nodes in the workflow.
      - Determine which required inputs are absent from the existing patches.
      - Prepend auto-generated patches for the missing inputs.

    Returns the number of patches injected.
    """
    patches = _parse_json_arg(tool_input.get("patches", "[]"))

    injected_count = 0
    new_patches: list[dict] = []

    for class_name, rule in NODE_VALIDATION_RULES.items():
        matching_nodes = _find_nodes_by_class(workflow, class_name)
        if not matching_nodes:
            continue

        required: frozenset[str] = rule["required_inputs"]
        defaults: dict = rule["defaults"]

        for node_id, _node in matching_nodes:
            # Collect which required inputs are already covered by existing patches
            existing_keys: set[tuple[str, str]] = {
                (str(p.get("node_id", "")), p.get("input_name", ""))
                for p in patches
                if isinstance(p, dict)
            }

            for input_name in sorted(required):  # sorted for deterministic ordering
                if (node_id, input_name) not in existing_keys:
                    auto_patch = {
                        "node_id": node_id,
                        "input_name": input_name,
                        "value": defaults[input_name],
                    }
                    new_patches.append(auto_patch)
                    injected_count += 1
                    logger.debug(
                        "pre_validation: injecting %s.%s = %r (node class: %s)",
                        node_id,
                        input_name,
                        defaults[input_name],
                        class_name,
                    )

    if new_patches:
        # Prepend auto-patches so they are applied before any agent-supplied patches,
        # allowing the agent's explicit values to override the auto-injected defaults.
        combined = new_patches + patches
        tool_input["patches"] = json.dumps(combined)

    return injected_count


class ModelSamplingFluxHandler(SteeringHandler):
    """Pre-validation handler: automatically injects missing required patches.

    Before every update_workflow call the handler:
      1. Loads the target workflow file from disk.
      2. Checks each node against NODE_VALIDATION_RULES.
      3. For any node type with known required inputs, injects missing patches
         with sensible defaults directly into the tool call (no LLM round-trip).
      4. Returns Proceed so the enriched call goes straight through.

    Because the agent's explicit patches are appended *after* the auto-injected
    ones, any value the agent already supplied takes precedence.

    Fallback behaviour: if the workflow file cannot be loaded or the JSON
    cannot be parsed, the handler returns Proceed without modification and
    lets update_workflow's own validation surface any errors.
    """

    name: str = "model_sampling_flux_guard"

    async def steer_before_tool(
        self, *, agent: Agent, tool_use: ToolUse, **kwargs: Any
    ) -> ToolSteeringAction:
        tool_name = tool_use.get("name", "")
        if tool_name != "update_workflow":
            return Proceed(reason="not an update_workflow call")

        tool_input = tool_use.get("input") or {}
        workflow_path = tool_input.get("workflow_path", "")

        if not workflow_path:
            return Proceed(reason="no workflow_path in tool input")

        workflow = _load_workflow_for_prevalidation(str(workflow_path))
        if not workflow:
            logger.debug(
                "pre_validation: could not load workflow at %r — skipping", workflow_path
            )
            return Proceed(reason="workflow could not be loaded; skipping pre-validation")

        injected = _inject_validation_patches(tool_input, workflow)

        if injected:
            logger.info(
                "pre_validation: auto-injected %d patch(es) before update_workflow",
                injected,
            )
            return Proceed(
                reason=f"pre-validation injected {injected} missing required patch(es)"
            )

        return Proceed(reason="pre-validation: no missing required patches")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_brain_steering_handlers(model=None) -> list:
    """Return the list of steering handler plugins for the Brain agent.

    Args:
        model: Unused — retained for API compatibility.  Both handlers are
               now rule-based and make zero LLM calls.

    Returns:
        List of SteeringHandler instances ready to pass as ``plugins=``.
    """
    return [
        BrainForbiddenToolHandler(),
        ModelSamplingFluxHandler(),
    ]
