---
name: assemble-from-template
description: Assembles a workfow on the basis of a brainbriefing JSON and a pre-selected template.
allowed-tools: update_workflow, get_workflow_template
---

This skill is used whenever you need to assemble and patch a workflow from a workflow template you have already selected. Uses the brainbriefing JSON to retrieve input- and output nodes.

**General constraints:**
- Before every tool call, state what you are doing and why.

Follow these steps:

### 1. Load template
Load the workflow template specified in the brainbriefing.
**Constraints:**
- You MUST call `get_workflow_template(brainbriefing.template_name)` and record the returned file path.
- You MUST NOT proceed if the template fails to load — report the error with `task_id` and stop.
- If the template is a **Nano Banana / Nano Banana 2 / Nano Banana Pro** variant: you MUST activate the `nano-banana` skill.
- If the template is a **z-Image** variant: you MUST activate the `zimage-turbo` skill.
- If the template is **`Kling3_multiShot`**: you MUST activate the `kling-multishot` skill and follow its Brain assembly steps instead of the standard step 2 patch procedure below.

### 2. Prepare updates and update the workflow template
- Start preparing workflow patches that can be used by the `update_workflow` tool in a single tool call: 
- provide a patch for every input node listed in the brainbriefing
- provide a patch for every output node listed in the brainbriefing
- provide a patch for positive prompt nodes, as described in the brainbriefing
- provide patches for any other nodes that need to be changed from the template (eg to apply parameters changes)
- the patches MUST follow the the format described by `update_workflow` doc string
- excesss input node removal: if `input_image_count` < number of existing image load nodes → provide a list of the the excess node IDs.
- add missing input nodes: if `input_image_count` > number of existing image load nodes → prepare a list of nodes to be added, match the format described by `update_workflow` tool's doc string.

- Update the workflow using the `update_workflow` tool.

**Constraints:**
- You MUST call `update_workflow(workflow_path, patches, add_nodes, remove_nodes)`. Use this tool to update the template in a single 
- You MUST NOT call `save_workflow()` — that tool is only for building entirely new workflows from scratch.
- `patches` MUST cover: positive prompt, negative prompt, resolution (width/height), input image nodes, output nodes, sampler settings, seed, steps, cfg. Each patch: `{"node_id": "6", "input_name": "text", "value": "..."}`.
  - `width` and `height` MUST come from `brainbriefing.resolution` — never guess.
- If the workflow contains a **ModelSamplingFlux** node: you MUST include all four required inputs in `patches` — see **ModelSamplingFlux patch requirements** at the end of this skill.
- If `update_workflow` returns `status: "error"`: you MUST read the reported problems, fix the patches, and call `update_workflow` again.
- If `count_iter > 1` AND `variations == true`: you MUST activate the `batch-handoff` skill (Mode A) to generate distinct prompts before patching. This corresponds to a **`batch_request`**: the **same workflow template** is executed N times with substituted parameters only — the workflow structure does not change between iterations.
- If you find a `BatchImagesNode` in the workflow template -- call `replace_node(workflow_path, <node_id>, "ImageBatch")` immediately. This tool preserves all connections automatically.

---

## ModelSamplingFlux patch requirements

When the workflow contains a `ModelSamplingFlux` node, all **four inputs** are required. Omitting any one will cause a ComfyUI validation failure.

### Required inputs

| input_name   | required value                                         |
|--------------|--------------------------------------------------------|
| `max_shift`  | `1.15`                                                 |
| `base_shift` | `0.5`                                                  |
| `width`      | from `brainbriefing.resolution_width`                  |
| `height`     | from `brainbriefing.resolution_height`                 |

### Patch template

Include these four patches in the `patches` array passed to `update_workflow`:

```json
[
  { "node_id": "<ModelSamplingFlux_node_id>", "input_name": "max_shift",  "value": 1.15 },
  { "node_id": "<ModelSamplingFlux_node_id>", "input_name": "base_shift", "value": 0.5  },
  { "node_id": "<ModelSamplingFlux_node_id>", "input_name": "width",      "value": <resolution_width>  },
  { "node_id": "<ModelSamplingFlux_node_id>", "input_name": "height",     "value": <resolution_height> }
]
```

Replace `<ModelSamplingFlux_node_id>` with the actual node ID from the workflow template. Replace `<resolution_width>` and `<resolution_height>` with the integer values from the brainbriefing.

### How to find the node ID

The `ModelSamplingFlux` node is typically listed in the `io.nodes` array returned by `get_workflow_template`. Look for `class_type: "ModelSamplingFlux"` and note its `nodeId`. If it is not in `io.nodes`, inspect the full workflow JSON for a node with `class_type: "ModelSamplingFlux"`.

### Rules

- You MUST include all four inputs in every `update_workflow` call that patches a ModelSamplingFlux node.
- Values are **not optional** — ComfyUI will reject the workflow if any of the four are absent.
- `width` and `height` MUST come from `brainbriefing.resolution_width` / `brainbriefing.resolution_height` — never hard-code or guess them.
