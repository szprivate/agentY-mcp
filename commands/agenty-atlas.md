---
description: Turn a picture or a prompt into a 3D scene with World Labs Atlas, then fly a camera through it or render new views.
argument-hint: <picture path(s) or a scene prompt> [camera move or view wanted]
---

Make a 3D scene and use it:

$ARGUMENTS

Read the `worldlabs-atlas` skill (`read_skill`; `camera-move-control` too when the goal is a
camera move for a video model). Start with `atlas_create_world`; grow it with
`atlas_expand_world`; get views with `atlas_render_view`, a camera move with
`render_camera_move`, and open it with `atlas_open_in_viewer`. Atlas jobs are paid and slow:
say what you are about to start before you start it.
