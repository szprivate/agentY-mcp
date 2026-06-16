---
name: batch-process
description: Run one workflow — or a chain of workflows — over MANY inputs (a folder of images/videos, or several attached files) as a single headless background job. Activate when the user wants to process/convert/upscale/restyle/animate a whole directory or a set of files in bulk, especially "run this over all of them", "process this folder", "do the same to each", or a multi-stage pipeline applied to every input. The job runs independently of the conversation and reports a pollable progress bar.
allowed-tools: start_batch_job get_batch_status stop_batch_job list_batch_jobs get_workflow_catalog get_workflow_template apply_brainbriefing update_workflow validate_workflow get_comfyui_dirs check_model run_script read_text_file
---

# batch-process — bulk runs as a headless background job

Use this when the work is **the same workflow (or a fixed chain of workflows)
applied across many inputs**. You assemble and validate each stage workflow
**once**, hand the job to a detached Python worker, and then just watch a
progress bar. The worker drives ComfyUI on its own — your context is free while
it runs, and no tokens are spent on the generation itself.

This is the right skill when the user says things like *"upscale every image in
this folder"*, *"turn each of these 30 stills into a 5-second clip"*, or
*"run background-removal then upscale on all of them"*. For a **single**
generation/edit use `comfyui-generate` instead.

## Pipeline model

For every input item the stages run **in order**, each stage's output file
feeding the next stage's input:

```
input ─▶ stage 1 ─▶ stage 2 ─▶ … ─▶ final output   (one final per input)
```

One stage = run that single workflow over every input. Two+ stages = chain them.

---

## Procedure

### 1. Resolve the inputs

- **A folder**: pass `"inputs": {"dir": "D:/path", "glob": "*.png"}` (omit `glob`
  to pick up common image/video types). Confirm the directory with the user if
  it's ambiguous.
- **Attached / specific files**: pass `"inputs": ["D:/a.png", "D:/b.mp4", …]`.
  A directory inside the list is expanded too.
- Don't upload inputs yourself — the worker stages each file into ComfyUI's
  input dir as it goes.

### 2. Build and VALIDATE one workflow per stage

For **each distinct stage** (most jobs have just one), do a normal single-item
assembly with the existing skills, but build it as a **reusable template** — the
worker swaps the input file and output name per item, so use any one input as
the stand-in:

1. `get_workflow_catalog` → `get_workflow_template(name)` (see **Selecting a Template** in `comfyui-core`).
2. Assemble with `apply_brainbriefing` / `update_workflow` (see
   `assemble-from-template`): set the prompt, resolve models with `check_model`,
   set resolution. **Leave the input file and output prefix as placeholders** —
   the worker overrides both per item.
3. `validate_workflow(workflow_path)` until it passes. Record the saved
   `workflow_path`.
4. Note the stage's **input node id + field** and **output node id**:
   - Input: the `LoadImage` (`image`) or `VHS_LoadVideo` (`video`) node.
   - Output: the `SaveImage` / `VHS_VideoCombine` node.
   - If the workflow has exactly one of each, you may omit them and let the
     worker auto-detect. If there are several, set them explicitly.

Repeat for stage 2, 3, … Make sure each stage's **input media type matches the
previous stage's output** (e.g. an image-to-video stage 1 must be followed by a
video-consuming stage 2).

### 3. Pick an output directory

Call `get_comfyui_dirs()` and set `output_dir` to a fresh subfolder under the
ComfyUI `output_dir` (e.g. `<output_dir>/batch_<short-name>`). Finals are copied
there, named per input.

### 4. Start the job

Call `start_batch_job(spec_json)` with:

```json
{
  "inputs": {"dir": "D:/in", "glob": "*.png"},
  "output_dir": "D:/comfy/output/batch_upscale",
  "stages": [
    {
      "workflow_path": "<validated stage1 workflow path>",
      "input_node_id": "190",
      "input_field": "image",
      "output_node_id": "9",
      "randomize_seed": false
    }
  ]
}
```

- `input_node_id` / `input_field` / `output_node_id` are **optional** — omit them
  to auto-detect when the workflow has a single load/save node.
- `randomize_seed` (default `false`): set `true` only if you want a fresh seed
  per item (usually leave off — each input already differs).

It returns a `job_id` **immediately**. Tell the user the job started and the id.

### 5. Watch progress

Call `get_batch_status(job_id)` to read the live bar:

- `state`: `starting` → `running` → `completed` (or `failed` / `stopped`).
- `progress_bar`, `completed_items` / `failed_items` / `total_items`.
- `current`: which item + stage is in flight.
- `errors`: most recent per-item failures (the job keeps going past a bad item).
- `outputs`: final files as items finish; `output_dir` for the whole set.

Poll when the user checks in (or each turn while monitoring) and relay the bar.
When `state` is `completed`/`failed`, report the counts, the `output_dir`, and
list a few outputs. If `alive` is `false` while `state` is still `running`, the
worker crashed — read `runner.log` in the job dir (`read_text_file`) and report.

### 6. Stop / list

- `stop_batch_job(job_id)` halts before the next item (finished items are kept).
- `list_batch_jobs()` shows recent jobs and their states.

---

## Rules

- Assemble + validate every stage workflow **before** calling `start_batch_job`
  — a stage that fails validation will fail on every single input.
- Do **not** loop `execute_workflow` per file — that blocks your context and
  spends tokens per item. The whole point of this skill is the headless worker.
- One `start_batch_job` call per batch. To change the recipe, start a new job.
- A single failing item does not abort the batch; check `errors` at the end and
  offer to re-run just the failures (a new job whose `inputs` are those files).
- Mixed-media chains must line up: each stage's input type = the prior stage's
  output type.
