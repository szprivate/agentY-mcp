---
description: Force the agentY generation pipeline (skip triage) — resolve a brainbriefing then assemble, validate, run, and QA the workflow.
argument-hint: <what to generate or edit>
---

Run the agentY **generation pipeline** directly on the request below, skipping
intent classification. Use this when you already know the request is a single
image/video generation, edit, chain, or batch.

## Request
$ARGUMENTS

## Do this
1. Invoke the **query-templates** subagent (Haiku) to resolve the request into a
   brainbriefing JSON. Pass along any attached image(s) and every user constraint
   (model, resolution, count, variations).
2. If it returns `status:"blocked"`, relay its question to the user and stop.
3. Otherwise invoke the **assemble-workflow** subagent (Sonnet) with that
   brainbriefing to assemble/patch, `validate_workflow`, `execute_workflow` (or
   `execute_workflows_batch` for a batch), and QA the output(s) with vision.
4. If execution fails and one corrective pass doesn't resolve it, invoke the
   **error-checker** subagent and hand its `fix_plan` back to assemble-workflow.
5. Report the saved output path(s) and a one-line QA verdict per output.
