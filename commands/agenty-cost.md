---
description: Price a workflow in credits before running it, and compare cheaper settings.
argument-hint: <workflow file path, or what you plan to run>
---

Price this before anything is run:

$ARGUMENTS

Use `estimate_workflow_cost` on the workflow file (for a single partner node, build it with
`partner_run` and `run=False` first). Tell me the per-node and total price (min and max),
the credit balance and the confirmation level, and any node whose price could not be worked
out. If a cheaper setting exists (lower resolution, shorter duration, fewer references),
estimate that too and show both. Run nothing.
