---
name: reference-scout
description: Find real visual references from the web and stage them as files for a generation/edit task. Activate when the request needs a real-world reference grounded in an actual image — a specific person, object, landmark, product, era, or art style — before generating. Produces a concise manifest of references, each marked for use as a direct image input or as a text description.
---

# Reference scout

Find the visual reference(s) the request needs, stage the best ones as files, and
summarise them. You do not generate or edit media here — only find and stage real
references from the web.

## Tools
- `web_search` — text search for context (what something looks like, correct names).
- `web_search_images` — image search; results include an `image_url` field.
- `download_image(image_url)` — stage an image into ComfyUI's input dir; returns
  `saved_to` (on-disk path), `name`, `subfolder`, `width`, `height`.
- `analyze_image` / `get_image_resolution` — verify a candidate matches the need
  (`analyze_image` returns the image for you to view).

## Procedure
1. **Identify the reference need(s)** — each distinct subject, object, location, era,
   or style the user wants grounded in a real reference. If none is needed, stop.
2. For each need, find candidates with `web_search_images` (and `web_search` for
   context). Pick the single best clear, relevant, high-quality image (at most 2 if
   genuinely needed). Avoid watermarked, tiny, or off-topic images.
3. `download_image(image_url)` to stage the chosen image; optionally `analyze_image`
   the staged file to confirm it matches before keeping it.
4. **Decide how each reference should be used:**
   - **image** — the exact look matters and should be fed directly to the generator
     as a visual input (`upload_image` already done by `download_image`; use the
     `name`/`subfolder`/`path`).
   - **text** — a written description is enough (a general mood, era, or style).
5. Write a concise, concrete **description** for every reference (used as text even
   in image mode).

## Output
Summarise the references you staged: for each, its `description`, its mode
(image/text), and for image-mode references the staged `path`, `name`, and
`subfolder` (so the generation step can wire it into a LoadImage node). Then hand off
to `comfyui-generate`, feeding the staged images in as `input_nodes` and the
descriptions into the prompt.
