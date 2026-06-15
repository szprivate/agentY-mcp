---
name: batch-handoff
description: Procedure for running a multi-iteration batch (count_iter > 1) — building the per-iteration workflow copies and executing them together. Activate after assembly when count_iter > 1.
allowed-tools: duplicate_workflow, update_workflow, execute_workflows_batch, read_text_file
---

# Batch execution — multi-iteration procedure

Activate when `count_iter > 1` in the brainbriefing. You build one workflow file per
iteration, collect their paths, then run them all with a single
`execute_workflows_batch([...paths...], brainbriefing_json)` call. That tool submits
every workflow up front, waits, and returns the output images for QA.

Two modes — determine from the brainbriefing:
- `variations == true` AND `count_iter > 1` → **Variations mode**
- `variations == false` AND `count_iter > 1` → **Identical mode**

---

## Mode A: Variations (distinct prompt per iteration)

Each iteration gets a unique prompt from `output_workflows/multiprompt.json`, produced
by the `image-batch` skill (run it first if not already done).

1. Read `output_workflows/multiprompt.json` via `read_text_file`.
2. **Iteration 1 (base):** `update_workflow(base_workflow_path, patches=[{"node_id": "<positive_prompt_node_id>", "input_name": "text", "value": "<prompt1>"}])`.
   Start a `paths` list with `base_workflow_path`.
3. **Iterations 2…N:** for each `promptN`:
   - `duplicate_workflow(base_workflow_path)` → `new_path`.
   - `update_workflow(new_path, patches=[{"node_id": "<positive_prompt_node_id>", "input_name": "text", "value": "<promptN>"}])`.
   - Append `new_path` to `paths`.
4. `execute_workflows_batch(paths, brainbriefing_json)`. Inspect the returned images.

---

## Mode B: Identical (same prompt, different seeds)

All iterations share the assembled workflow; `duplicate_workflow` assigns a fresh
random seed to each copy.

1. **Iteration 1 (base):** ensure `update_workflow` returned `status: "ok"` in
   assembly. Start a `paths` list with `base_workflow_path`.
2. **Iterations 2…N:** `duplicate_workflow(base_workflow_path)` → `new_path`; append to `paths`.
3. `execute_workflows_batch(paths, brainbriefing_json)`. Inspect the returned images.

---

## Rules (both modes)

- Build exactly `count_iter` workflow paths — never skip an iteration.
- Do NOT call `submit_prompt` or `execute_workflow` per iteration — collect the paths
  and make ONE `execute_workflows_batch` call.
- If `duplicate_workflow` fails, report it and stop; don't guess an alternative path.
- If `update_workflow` keeps erroring on a duplicate, report the error and stop after
  3 retries.
