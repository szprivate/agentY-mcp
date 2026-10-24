---
description: Generate or edit an image or video with agentY (template or partner model), price-checked, validated and looked at.
argument-hint: <what to make or change, plus model / size / count if you care>
---

Make this with agentY's tools (delegate to the `agenty` agent when it is a long job):

$ARGUMENTS

1. `list_skills`, then `read_skill` the ones that match: `workflow-templates` and
   `prompting` for a normal job, `partner-run` when a partner model is named,
   `assemble-from-template` / `assemble-new-workflow` for building, `dashscope-generate`
   for DashScope, `deadline-farm` for the render farm.
2. Pick a template (`get_workflow_catalog`, `get_workflow_template`) or run the named
   partner node (`partner_run`); `check_model` for models.
3. Paid nodes: `estimate_workflow_cost` first, tell me the price and ask when it is above
   the confirmation level.
4. `validate_workflow`, then `execute_workflow` (`run_variants` for several versions).
5. Look at the outputs and tell me the paths and whether they match the request.
