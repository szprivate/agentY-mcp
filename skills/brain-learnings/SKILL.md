---
name: brain-learnings
description: Auto-populated learnings from past high-iteration problem-solving sessions. Activate this skill when you notice you are making repeated tool calls to solve the same sub-problem, or when the same error keeps appearing. The entries below document past problems and proven solutions — consult them before retrying a failing pattern.
allowed-tools: 
---

# Brain Self-Learnings

> **This file is automatically maintained by the learnings agent.**
> It is appended after any session where the Brain used more than 5 tool calls.
> Do **not** edit the "Learnings Log" section manually.

## When to activate this skill

Activate and consult this skill when you observe any of the following:
- You have already made **3 or more tool calls** attempting to fix the same issue.
- A tool call fails and you are about to retry with the same approach.
- You are uncertain how to proceed and the task feels repetitive.

Scan the learnings log below for entries that match your current situation.
If a matching entry exists, **apply the documented solution directly** instead of re-discovering it.

---

## Learnings Log

<!-- The learnings agent automatically appends new entries below this line. -->
<!-- Format: date | problem summary | solution (1–2 sentences) -->
2026-05-12 | CLIPLoader validation fails with incorrect clip_name or missing type | Use get_node_schema to identify the exact clip_name string and the required type value.

2026-05-12 | CLIPLoader validation fails when clip_name lacks subfolder prefix | Use the full path including the subfolder prefix, such as FLUX2\\, to match the server's expected model name list.

2026-06-07 | update_workflow fails when resolution values are not in a node's predefined list | Check node schema for allowed enum values and select the nearest option (e.g., '2K') when specifically requested dimensions are not supported by the system.

2026-06-07 | apply_brainbriefing fails when positive_prompt_node_id is null in brainbriefing | Identify the prompt node via get_workflow_node_info, then use update_workflow to patch the prompt input directly to that node.
2026-06-07 | batch variations require multiprompt.json before batch-handoff execution | Generate distinct prompts using write_text_file to output_workflows/multiprompt.json with keys prompt1..promptN before duplicating workflows.

2026-06-07 | LoadImage validation fails when filename lacks subfolder prefix | Qualify the filename with its subfolder path (e.g., 'agent/image_edit_00005_.png' instead of just 'image_edit_00005_.png') to match ComfyUI input directory structure.

```
2026-06-07 | LoadImage validation fails when image filename lacks subfolder prefix | Qualify the filename with its full subfolder path (e.g., 'agent/filename.png') to match ComfyUI input directory structure; unqualified names cause custom_validation_failed errors.
```
