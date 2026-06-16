---
name: comfyui-generate
description: End-to-end procedure for turning a natural-language request into a generated or edited image/video via the agentY ComfyUI MCP server. Activate whenever the user asks to generate, create, render, edit, upscale, restyle, or animate an image or video (text-to-image, image-to-image, inpaint, image-to-video, batches, variations, multi-step pipelines). Orchestrates template selection, prompt writing, model resolution, workflow assembly, validation, execution, and visual QA.
---

# agentY — ComfyUI generation orchestrator

You are the single orchestrator. You read the request, build the workflow with the
agentY MCP tools, run it, look at the result, and iterate. There is no separate
Researcher/Brain/Executor — you do all of it. Work concretely: resolve every value
with a tool call rather than guessing, and say what you are about to do before each
tool call.

## 0. Classify the request first

- **Question only** ("what templates exist?", "which model does X use?") → answer
  using `get_workflow_catalog`, `get_workflow_template`, `check_model`,
  `search_nodes`. No generation.
- **Single generation/edit** → follow steps 1–6 below once.
- **Multi-step pipeline** (structurally different stages in sequence, e.g.
  text-to-image → upscale → image-to-video) → plan the stages yourself, then run
  steps 1–6 for each stage, feeding each step's output file(s) into the next as
  inputs (`upload_image`).
- **Batch / variations** (same workflow run N times) → set `count_iter > 1`;
  for distinct prompts per run set `variations: true` and use the `batch-handoff`
  skill (Mode A), then `execute_workflows_batch`.
- **Bulk over many inputs** (a folder of files, or several attached images/videos
  run through one workflow or a chain of workflows — "process this folder", "do
  the same to each", "upscale all of these") → use the `batch-process` skill. It
  assembles each stage once and hands the whole set to a headless background
  worker you poll for progress, instead of running steps 1–6 per file.
- **Annotated image** (user drew/circled/marked on an image) → activate the
  `annotation` skill instead of the normal input/template steps.
- **Follow-up on a previous result** ("make it darker", "now 16:9") → reuse the
  prior workflow/output; re-patch and re-run rather than starting over. See the
  `feedback-loop` skill.

## 1. Build a brainbriefing (your internal plan)

Resolve the request into a **brainbriefing** — a structured JSON plan that
`apply_brainbriefing` consumes. See `references/brainbriefing.md` for the schema and
an example. Fill every field from tool results:

- **Inputs**: analyse any provided image with `analyze_image` (it returns the image
  for you to view). Set `input_image_count` to the exact number of input images.
  To reuse a prior output as an input, `upload_image(file_path=...)` and use the
  returned `name` as the filename and `<input_dir>/<name>` as the path.
- **Template** (step 2), **prompt** (step 3), **models** (step 4), **resolution**:
  use `get_image_resolution` for a provided master image; otherwise pick a sensible
  size for the model/aspect.
- **Output nodes**: call `get_comfyui_dirs()` for `output_dir`; set each output
  node's `output_path` to `<output_dir>/<task_subfolder>` — see **Output path /
  task-subfolder mapping** at the end of this skill for `task_subfolder` naming.

## 2. Select a template

See **Selecting a Template** in the `comfyui-core` skill for matching rules. Never guess names — call
`get_workflow_catalog` then `get_workflow_template`. Priority: exact name > similar
name > task-type > model-family. If nothing matches, set `template.name = "build_new"`
and follow the `assemble-new-workflow` skill. Don't stop to ask — pick a sensible
default and note assumptions.

## 3. Write the prompt

Activate the `prompt-craft` skill and follow its model-family rules. For the
`Kling3_multiShot` template, use the `kling-multishot` skill instead. No filler or
generic quality tokens.

## 4. Resolve models

For every model the workflow references (from `get_workflow_template`'s `models`),
call `check_model([...])`. Use the returned relative path verbatim. If a model is
missing, escalate: `find_hf_file` → `download_hf_model` (pass `node_class_type`); fall
back to `search_huggingface_models` + `get_model_info`. Never hallucinate model paths.

## 5. Assemble & validate

- **Template path**: `get_workflow_template(name)` → record `workflow_path`, then
  `apply_brainbriefing(workflow_path, brainbriefing_json)` (one call patches inputs,
  prompts, outputs, resolution). Use the `assemble-from-template` skill for the
  details and the special-case node fixes (e.g. `BatchImagesNode` → `replace_node`
  to `ImageBatch`; `ModelSamplingFlux` → the ModelSamplingFlux patch requirements
  in `assemble-from-template`).
- **Build-new path**: follow `assemble-new-workflow`, then `save_workflow`.
- If `apply_brainbriefing` returns `status: "error"`, read `problems`/`server_errors`
  and apply ONE corrective `update_workflow(workflow_path, patches)` pass.
- Finish with `validate_workflow(workflow_path)` and fix reported issues.

## 6. Execute & QA

- **Single run**: `execute_workflow(workflow_path, brainbriefing_json)`.
- **Batch / variations**: `duplicate_workflow` per iteration (or `batch-handoff`
  Mode A for per-variation prompts), then `execute_workflows_batch([...paths...])`.
  See `batch-handoff`.

`execute_workflow` submits, waits, and **returns the output image(s)** (or sampled
video frames). **Look at them.** Judge whether they satisfy the request — subject,
style, composition, edit fidelity, no artifacts. If they fall short, diagnose (use
`troubleshooting` for execution failures; `get_logs` for errors) and re-patch +
re-run. Report the saved output paths to the user.

## Memory

At the start of a task you MAY `memory_read` for relevant user preferences. After
learning something durable (a preferred resolution, a model that worked well, a
recurring subject), `memory_write` one concise sentence. See `brain-learnings`.

## Output path / task-subfolder mapping

Set `output_path` for each entry in `output_nodes` as `<output_dir>/<task_subfolder>`,
using the `task_subfolder` from this table.

### Primary mapping (by task type)

| Task type          | task_subfolder      |
|--------------------|---------------------|
| `image_generation` | `image_generation`  |
| `image_edit`       | `image_edit`        |
| `video_i2v`        | `video_i2v`         |
| `video_flf`        | `video_flf`         |
| `video_v2v`        | `video_v2v`         |
| `audio`            | `audio`             |
| `3d`               | `model`             |

### Inference rules for ambiguous cases

If the task type is not explicitly determinable from the user request, infer it from the output node's `class_type`:

| Output node class_type        | Inferred task type  | task_subfolder      |
|-------------------------------|---------------------|---------------------|
| `SaveImage`, `PreviewImage`   | `image_generation`  | `image_generation`  |
| `VHS_VideoCombine`            | check input nodes — if has image input → `video_i2v`, else `video_v2v` |
| `SaveAudio`, `VHS_SaveAudio`  | `audio`             | `audio`             |
| `Save3DModel`, `TripoSG_*`    | `3d`                | `model`             |

**Image edit vs image generation**: if the workflow has any `LoadImage`, `VHS_LoadImagePath`, or similar input node AND the primary output is `SaveImage`, check the template name or user request for the word "edit" / "inpaint" / "modify". If found → `image_edit`. Otherwise → `image_generation`.

**VHS_VideoCombine ambiguity**:
- Input nodes include a LoadImage / VHS_LoadImagePath → `video_i2v`
- Input nodes are text-only → check if template name contains `flf` (first-last-frame) → `video_flf`
- Otherwise → `video_v2v`

### Rules

- Every entry in `output_nodes` MUST have an `output_path`.
- If there are multiple output nodes of the same type (e.g. two SaveImage nodes), they share the same `output_path`.
- Never guess a custom path — use only the task-subfolders listed above.
