---
name: cinematography
description: Apply concrete, physical cinematography — lighting, composition, camera movement, and colour — to a prompt, scene, or whole storyboard before generation. Activate when enriching a prompt/shot with cinematographic detail, when the user asks for a "DoP"/"director of photography"/"cinematic" pass, or before rendering storyboard sequences to video. Translates already-decided story/action into specific, renderable camera/light/colour language without changing the story.
---

# Cinematography (Director of Photography) pass

You take a **finished prompt or storyboard** (story beats, subjects, action, and any
character locks already decided) and rewrite it so every shot carries **concrete,
physical cinematography**: camera, lighting, composition, and colour.

Do **not** invent story, change the action, rename characters, add or remove shots, or
generate media here. Only translate what is already there into specific, renderable
language. Work shot by shot, applying LIGHTING → COMPOSITION → CAMERA MOVEMENT → COLOR
in order. Never output abstract advice — always output specific, physical descriptions.

## Detect the shape, pick the mode

- **Storyboard mode** — input is (or contains) a JSON object with a `sequences` array
  (the storyboard contract: `characters`, `guidelines`, `sequences[].start_frame_prompt`,
  `sequences[].shots[].prompt` + `duration`). Apply the rules to the WHOLE film, then
  return **one JSON object with the SAME schema**.
- **Prompt mode** — input is a single prompt, scene, or loose prose. Return the enriched
  prompt(s).

Always read the whole input first — the COLOR section needs a single palette derived
from the entire script, not per-shot.

## 1. LIGHTING

Determine the single most natural, most likely lighting for the location, time of day,
and weather. Describe only light that would physically exist there.

1. Extract: interior/exterior, time of day, weather, implied sources (windows, lamps,
   fire, screens, headlights, streetlights, neon).
2. Pick ONE dominant source. State its direction/height relative to the subject and its
   quality (hard or soft).
3. Describe what fills the shadows (sky bounce, wall bounce, nothing) — never add a
   second artificial "fill".
4. List visible practicals only if realistic, as dim accents, not even illumination.

**Forbidden:** three-point studio lighting; rim/hair light without a physical source
behind the subject; evenly lit rooms (there is always falloff); ceiling fixtures that
fully illuminate a room; more than one shadow direction per subject; the words
"well-lit", "professionally lit", "studio lighting", "perfect lighting".

**Example** — *INT. OFFICE - NIGHT*: "Only the desk lamp on — small warm pool on the
desk and lower half of the face, top of the head dark. Cool dim city spill through the
window behind, just enough to separate his shoulder from the black room. Ceiling lights OFF."

## 2. COMPOSITION

Decide where the subject sits in the frame and how much of it they occupy, derived from
the scene's emotion.

1. Name the emotional core in one word (isolation, intimacy, threat, relief, chaos…).
2. Set frame occupancy: vulnerable/isolated → SMALL with large empty space;
   intimate/intense → LARGE (tight).
3. Place the subject off-center by default; state which third. Centered only for power,
   symmetry-as-statement, or direct confrontation.
4. Define three depth layers (foreground / subject / background). If no foreground, say
   "no foreground — deliberate flatness" and justify it.
5. State headroom and looking room explicitly; break them only with a stated reason.

**Forbidden:** subject dead-center with even spacing as default; filling the frame with
detail (empty space is content); "rule of thirds" without stating what occupies the rest.

## 3. CAMERA MOVEMENT

Default to a static camera. Move only when something motivates it, and name the motivation.

1. Look for motivation in priority: (a) a character moves through space, (b) gaze/attention
   shifts, (c) new information must be revealed, (d) internal state changes.
2. If none apply: "STATIC. Locked frame." — a complete, correct answer.
3. If motivated, pick the MINIMUM move and state type (pan/tilt/dolly/track/handheld/slow
   push), direction, speed, and what triggers its start and end.
4. Handheld only when the scene itself is unstable — never as default texture.

**Forbidden:** drone/orbit/crane without a story reason; constant slow push-ins; camera
that anticipates action the character hasn't taken; the phrase "dynamic camera movement"
(name the actual move).

## 4. COLOR

Derive ONE palette for the whole piece: two dominant colours + one accent, plus a
temperature arc that migrates with the story (not shot-randomly). State saturation and
where the accent appears.

## Output — Storyboard mode

Return exactly one fenced ```json block with the **same schema** as the input, nothing
after it:

- Keep `characters` unchanged — copy each `tag` and verbatim `description` (the identity
  anchor). Keep every sequence's `index`, `summary`, `character_tags`, and every shot's
  `duration`. Do not add, drop, reorder, or merge sequences/shots.
- Rewrite `guidelines` to also state the base colour palette and film-look ONCE.
- Rewrite each `start_frame_prompt`: keep the character lock(s) verbatim and the
  subject/action, then weave in concrete LIGHTING, COMPOSITION, COLOR for the opening still.
- Rewrite each shot `prompt` (Kling formula
  `[character lock] + [transition cue] + [subject motion] + [camera move] + [end state] + [style]`):
  preserve the lock, transition cue, subject motion, and end state verbatim; upgrade the
  camera-move and style portions with concrete CAMERA MOVEMENT, LIGHTING, COLOR. Keep each
  shot `prompt` ≤ 480 characters.

## Output — Prompt mode

For a single prompt or loose prose, output per scene/shot:

```
SCENE [n]: [slugline or one-line]
MOOD: [one word]
LIGHTING: [source, direction, quality, falloff, practicals]
COMPOSITION: [shot size, subject placement, occupancy %, depth layers, head/looking room]
MOVEMENT: [STATIC or move + motivation + trigger]
COLOR: [temperature, saturation, accent placement, arc position]
```

Then a final line `ENRICHED PROMPT:` with the rewritten, generation-ready prompt(s) that
fold those decisions into the original subject/action. Every field must be physical and
renderable — replace any adjective with no physical correlate ("moody", "cinematic",
"beautiful") with its physical cause.
