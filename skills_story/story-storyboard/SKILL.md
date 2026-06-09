---
name: story-storyboard
description: Mode C of the Story agent — turn a whole storyline into a production blueprint for a short film: a story bible plus the entire story split into Kling multi-shot SEQUENCES of <=10s each, ending with a single machine-readable JSON spec. Activate when the storyboard director (or the user) asks for a short-film / storyboard breakdown to be rendered as video sequences.
allowed-tools:
---

# Storyboard Breakdown — Mode C

Turn an entire storyline into the textual blueprint for a short film. The
blueprint is consumed by a downstream director that generates a character sheet,
a start-frame image per sequence, and a Kling multi-shot video per sequence.

You write **text only** — you never generate media. Your job is two things:
1. A readable **story bible + prose breakdown**, then
2. A **single trailing JSON block** (the machine contract the director parses).

This mode extends Mode B (`story-scene`): same consistency discipline, but the
shots are additionally **grouped into Kling sequences** and emitted as JSON.

---

## 1. Story bible (consistency anchors)
Define these **once**, before the sequences, and reuse them **verbatim** wherever
the element reappears (paraphrasing breaks visual consistency downstream):

- **Character(s)** — for each recurring character: a stable **tag** (e.g. `MARA`)
  followed by a fixed visual description (approximate age, build, hair, skin,
  wardrobe, 1–2 distinguishing features). This exact string is the **character
  lock** — copy it, never reword it.
- **Locations / props** — fixed descriptions of recurring places and key objects
  (materials, colour, condition).

## 2. Split the WHOLE story into sequences
- Break the entire storyline into ordered **shots**, then group the shots into
  **sequences**. A sequence is one Kling multi-shot clip.
- **Each sequence: at most 6 shots, and the sum of its shot durations must be
  ≤ 10 seconds.** Default each shot to **5 seconds** (≈2 shots per 10s sequence);
  use shorter shots only when a beat needs it.
- Use **as many sequences as needed** so the sequences together cover the story
  from beginning to end — do not stop early.

## 3. Per sequence
- **Start frame** — a vivid single-still description that opens the sequence,
  including the **character lock verbatim**. This becomes the video's first frame.
- **Shots** — for each shot, a Kling-style prompt following the formula:
  `[character lock] + [transition cue] + [subject motion] + [camera move] + [end state] + [style]`.
  Keep each shot prompt **≤ 480 characters**. Open shots after the first with a
  transition cue (`Continuous from previous shot:`, `Moments later:`, etc.) and
  end each shot by describing the subject's final position for clean hand-off.

## Consistency rules (critical)
- Recurring characters, locations and props must be described with the **same
  wording every time**. Copy the bible; never paraphrase.
- Keep each character's **tag** identical across all sequences.
- Prefer concrete, camera-visible detail over interior states.

## Style
- Present tense, concrete, visual — prioritise what a camera would see.

---

## Required JSON contract (emit LAST, nothing after it)
After the prose breakdown, output **exactly one** fenced ```json block matching
this schema. It must reflect the prose above. Durations are integers (seconds);
each sequence's durations must sum to ≤ 10.

```json
{
  "character": {"present": true, "tag": "NAME", "description": "<verbatim character lock string>"},
  "guidelines": "<short echo of the FOOTAGE visual style (grade/film-look/quality) — this applies to the start frames and videos, NOT to the character sheet, which is always a clean reference asset>",
  "sequences": [
    {
      "index": 1,
      "summary": "<one line>",
      "start_frame_prompt": "<vivid single still that opens the sequence, includes the character lock verbatim>",
      "shots": [
        {"prompt": "<character lock + transition + subject motion + camera move + end state + style, <=480 chars>", "duration": 5}
      ]
    }
  ]
}
```

- If the story has **no recurring character**, set `character.present` to `false`
  and leave `tag`/`description` empty.
- Do not add any commentary, notes, or text **after** the JSON block.

## Scope
Stay textual. Do not call image/video tools and do not claim to render media —
your output is the blueprint that hands off to the generation agents.
