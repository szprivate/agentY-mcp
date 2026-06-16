# Brainbriefing schema

The **brainbriefing** is the structured JSON plan you build for a generation/edit
task and pass (as a JSON string) to `apply_brainbriefing(workflow_path, brainbriefing_json)`
and to `execute_workflow(workflow_path, brainbriefing_json)`. It tells those tools
which nodes carry inputs, prompts, and outputs, and where to save results.

## Field reference

- `status` — `"ready"` or `"blocked"`. Use `"blocked"` only when a hard blocker
  remains (a required input image is missing, a required model can't be found or
  downloaded). Otherwise `"ready"`.
- `blockers` — list of blocker/warning strings (defaulted params, substituted models).
- `task.type` — one of: image edit | image generation | video flf | video i2v |
  video v2v | audio.
- `task.description` — one sentence.
- `template.name` — the selected template name, or `"build_new"` when none fits.
- `input_images[]` — `{filename}` per provided input image.
- `input_nodes[]` — full ComfyUI binding per input image:
  `{node_id, filename, role, node, slot, path}`. `role` ∈ master_image |
  reference_image | mask | depth_map | control_image. `node_id`/`node`/`slot` come
  from the template's `io.inputs`; `path` is the on-disk file.
- `input_image_count` — MUST equal `len(input_images)`.
- `output_nodes[]` — `{node_id, node, output_path}` per output node
  (`is_output_node: true`, e.g. SaveImage, VHS_VideoCombine, SaveAudio).
  `output_path` = `<get_comfyui_dirs().output_dir>/<task_subfolder>`.
- `resolution_width` / `resolution_height` — pixels. From `get_image_resolution`
  when a master image is provided; otherwise a sensible size for the model/aspect.
- `prompt.positive` / `prompt.negative` — generation prompts (negative may be null).
- `prompt_nodes[]` — `{node_id, role, slot, node}` per prompt-receiving node;
  `role` ∈ positive | negative; `slot` is usually `"text"`.
- `count_iter` — number of iterations (1 = single run; 2–20 = batch).
- `variations` — `true` when each iteration uses a distinct prompt (needs the
  `image-batch` skill); else `false`.
- `positive_prompt_node_id` — node id of the positive prompt node when
  `variations == true` and `count_iter > 1`; otherwise `null`.

## Example

```json
{
  "status": "ready",
  "blockers": [],
  "task": { "type": "image generation", "description": "one sentence" },
  "template": { "name": "... or build_new" },
  "input_images": [{ "filename": "..." }],
  "input_nodes": [
    {
      "node_id": "25",
      "filename": "...",
      "role": "master_image",
      "node": "VHS_LoadImagePath",
      "slot": "image",
      "path": "path to the image"
    }
  ],
  "input_image_count": 0,
  "output_nodes": [
    { "node_id": "42", "node": "SaveImage", "output_path": "<output_dir>/image_generation" }
  ],
  "resolution_width": 1024,
  "resolution_height": 1024,
  "prompt": { "positive": "...", "negative": "... or null" },
  "prompt_nodes": [
    { "node_id": "6", "role": "positive", "slot": "text", "node": "CLIPTextEncode" }
  ],
  "count_iter": 1,
  "variations": false,
  "positive_prompt_node_id": null
}
```
