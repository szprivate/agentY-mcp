---
name: feedback-loop
description: Handle a follow-up request that refines, tweaks, chains from, or corrects a generation you produced earlier in the conversation. Activate when the user reacts to a previous result (e.g. "make it darker", "higher resolution", "different seed", "now upscale it", "turn it into a video", "that's the wrong style") instead of starting a brand-new task.
---

# Follow-up request handler

A follow-up builds on something you already generated in this conversation. You
already have the prior workflow path, the brainbriefing, the input paths, and the
output paths from your earlier tool calls — reuse them instead of starting over.

## Tweak (adjust parameters of the last run)

The user wants to change style, resolution, seed, strength, steps, cfg, prompt, LoRA,
etc., without changing the overall task.

1. Reuse the prior workflow file on disk (the path your earlier `get_workflow_template`
   / `save_workflow` / `update_workflow` returned). Do NOT reload the template fresh.
2. Identify exactly which parameter(s) to change from the user's message.
3. `patch_workflow(workflow_path, patches)` with only the targeted changes.
4. `validate_workflow(workflow_path)` and fix any errors.
5. `execute_workflow(workflow_path, brainbriefing_json)` and inspect the returned image(s).

Examples: "more saturated" → cfg/prompt; "different seed" → seed node; "higher
resolution" → width/height nodes; "add a LoRA" → patch/add a LoRA loader node.

## Chain (pipe the last output into a new workflow)

"Now upscale it", "turn it into a video", "make a 3D model from it".

1. Use the previous run's output file(s) as input: `upload_image(file_path=<prior output>)`.
2. Select the new template (see **Selecting a Template** in `comfyui-core`) and build a fresh brainbriefing
   for the new task, following `comfyui-generate` steps 1–6, with the uploaded files as
   `input_nodes`.
3. Execute and inspect the result.

## Correction (fix a mistake you made)

Wrong template, wrong model, bad output, or a failed tool call.

1. From the conversation + `get_logs` (for execution errors), identify the root cause.
2. Apply the minimum fix — don't redo steps that already succeeded:
   - Wrong template → re-select and rebuild from step 2 of `comfyui-generate`.
   - Patch/validation error → re-patch the existing workflow → re-validate → re-execute.
   - Quality/QA failure → re-run with a different seed or adjusted parameters.
3. Execute and inspect the result.

## Rules
- Briefly acknowledge what you're changing (one line) before acting.
- Never ask "should I proceed?" — act immediately.
- Only ask a clarifying question if the prior context is genuinely unrecoverable.
