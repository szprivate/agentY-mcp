---
description: Destroy a 3D model in Houdini (collapse, break, knock over) with a rigid-body sim, dust and a flipbook or Karma render.
argument-hint: <the model file or scene> <how it should fall apart>
---

Destroy this in Houdini:

$ARGUMENTS

Read the `dcc-destruction-houdini` skill (`read_skill`) and follow it. The build goes through
`dcc_build` with `app="houdini"` (batch mode); check the frames with `video_frames` and
`media_info`, look at them with `analyze_image`, and show me the result.
