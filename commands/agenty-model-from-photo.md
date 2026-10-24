---
description: Model a building, object or room in Blender, Maya or Houdini so it matches a reference photo.
argument-hint: <photo path(s)> [app: blender|maya|houdini] [what to model]
---

Model this in a 3D app to match the photo:

$ARGUMENTS

Read the `model-from-reference` skill (`read_skill`) and follow its stages exactly: measure
the photo (`measure_reference`), match the camera, block out until `dcc_silhouette_check`
passes, then details, then materials and light. Build with ONE script run by `dcc_build`
(never live edits). `reverse_image_search` finds more photos of the same object when one
view is not enough. Show me the render and the numbers from the check.
