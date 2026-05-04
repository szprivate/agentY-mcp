---
name: video-ltx2-3-flf2v
description: "Patch and validate [image-to-video] workflows. Activate when brainbriefing template name contains 'video_ltx2_3_flf2v'. Patchable: Input images / video, Resolution, Seed, Length / FPS, Prompts, Output; Locked: Structural nodes, Sampler recipe, and Resolution-driven logic."
allowed-tools: patch_workflow check_model
---

# Video Ltx2 3 Flf2V workflow assembly

Assembles and validates image-to-video workflows using LTX-Video.

---

## Workflow shape

- **Inputs:** image
- **Output:** video (VHS container)
- **Model:** `ltx-2.3-22b-distilled-fp8.safetensors`, `ltx-2.3-22b-distilled-fp8.safetensors`
- **Sampler:** N/A
- **CFG:** ? (distilled — never raise)

---

## Patchable nodes — the ONLY things you may change

All patches go through `patch_workflow({node_id, input_name, value})`.

### Input images / video

| Node | Type | Input | Notes |
|---|---|---|---|
| `31` | `LoadImage` (Load First Frame) | `image` | Do not touch node `124` — reads from this automatically. |
| `39` | `LoadImage` (Load Last Frame) | `image` | Do not touch node `125` — reads from this automatically. |

### Resolution

| Node | Type | Input | Notes |
|---|---|---|---|
| `98` | `PrimitiveInt` (HEIGHT) | `value` | Do not touch node `124`, `125` — reads from this automatically. |
| `113` | `PrimitiveInt` (WIDTH) | `value` | Do not touch node `124`, `125` — reads from this automatically. |

### Seed

| Node | Type | Input | Notes |
|---|---|---|---|
| `100` | `RandomNoise` (RandomNoise) | `noise_seed` | Do not touch node `120` — reads from this automatically. |

### Length / FPS

| Node | Type | Input | Notes |
|---|---|---|---|
| `102` | `PrimitiveInt` (Length) | `value` | Must satisfy length = 8n + 1 (e.g. 49, 73, 97, 121, 161). Do not touch node `101`, `108` — reads from this automatically. |

### Prompts

| Node | Type | Input | Notes |
|---|---|---|---|
| `112` | `CLIPTextEncode` (CLIP Text Encode (Prompt)) | `text` | Must include a `Music: <style>` line — parsed by the audio decoder. Do not touch node `109` — reads from this automatically. |
| `128` | `CLIPTextEncode` (CLIP Text Encode (Prompt)) | `text` | Must include a `Music: <style>` line — parsed by the audio decoder. Do not touch node `109` — reads from this automatically. |

### Output

| Node | Type | Input | Notes |
|---|---|---|---|
| `130` | `VHS_VideoCombine` (Video Combine 🎥🅥🅗🅢) | `filename_prefix` |  |
| `130` | `VHS_VideoCombine` (Video Combine 🎥🅥🅗🅢) | `format` |  |
| `130` | `VHS_VideoCombine` (Video Combine 🎥🅥🅗🅢) | `crf` |  |

Always upload input files via `upload_image` before patching.

### LTXV Guide nodes (semi-patchable)

| Input | Valid range | Note |
|---|---|---|
| `strength` | 0.5–0.9 | Asymmetric values cause instability. |


---

## DO NOT TOUCH — these nodes are fixed

### Model loaders

| Node | Reason |
|---|---|
| `103` `LTXAVTextEncoderLoader` (LTXV Audio Text Encoder Loader) | Loads `gemma_3_12B_it_fp4_mixed.safetensors`, `ltx-2.3-22b-distilled-fp8.safetensors` — swap not safe without full reconfig. |
| `126` `LTXVAudioVAELoader` (LTXV Audio VAE Loader) | Loads `ltx-2.3-22b-distilled-fp8.safetensors` — swap not safe without full reconfig. |

Use `check_model` to verify each file is present locally and resolve its full path
before patching the node. Missing models are handled upstream by the Researcher
(HuggingFace download) — the Brain's job is path resolution, not availability checking.

### Locked structural nodes

| Node | Reason |
|---|---|
| `99` `LTXVPreprocess` (LTXVPreprocess) | Auto-driven by resolution primitives. |
| `101` `LTXVEmptyLatentAudio` (LTXV Empty Latent Audio) | Structural node — do not patch. |
| `104` `LTXVPreprocess` (LTXVPreprocess) | Auto-driven by resolution primitives. |
| `105` `VAEDecodeTiled` (VAE Decode (Tiled)) | Structural node — do not patch. |
| `106` `LTXVCropGuides` (LTXVCropGuides) | Pure wiring — do not patch. |
| `107` `LTXVAudioVAEDecode` (LTXV Audio VAE Decode) | Structural node — do not patch. |
| `108` `EmptyLTXVLatentVideo` (EmptyLTXVLatentVideo) | Structural node — do not patch. |
| `109` `LTXVConditioning` (LTXVConditioning) | Conditioning node — do not patch. |
| `110` `GetImageSize` (Get Image Size) | Auto-driven by resolution primitives. |
| `111` `LTXVAddGuide` (LTXVAddGuide) | Pure wiring — do not patch. |
| `114` `PrimitiveInt` (Frame Rate(int)) | Structural node — do not patch. |
| `115` `LTXVAddGuide` (LTXVAddGuide) | Pure wiring — do not patch. |
| `116` `CFGGuider` (CFGGuider) | Sampler recipe — do not change. |
| `117` `SamplerEulerAncestral` (SamplerEulerAncestral) | Sampler recipe — do not change. |
| `118` `ManualSigmas` (ManualSigmas) | Checkpoint-matched sigma schedule — do not change. |
| `119` `LTXVConcatAVLatent` (LTXVConcatAVLatent) | Pure wiring — do not patch. |
| `120` `SamplerCustomAdvanced` (SamplerCustomAdvanced) | Sampler recipe — do not change. |
| `121` `LTXVSeparateAVLatent` (LTXVSeparateAVLatent) | Pure wiring — do not patch. |
| `122` `CreateVideo` (Create Video) | Structural node — do not patch. |
| `123` `ComfyMathExpression` (Math Expression) | Math passthrough — reads from upstream primitive. |
| `124` `ResizeImageMaskNode` (Resize Image/Mask) | Auto-driven by resolution primitives. |
| `125` `ResizeImageMaskNode` (Resize Image/Mask) | Auto-driven by resolution primitives. |
| `127` `CheckpointLoaderSimple` (Load Checkpoint) | Structural node — do not patch. |
| `129` `GetVideoComponents` (Get Video Components) | Structural node — do not patch. |

---

## Validation checklist

1. Image inputs uploaded and patched into nodes `31`, `39`.
2. Positive and negative prompt nodes patched with user brief text.
3. Length value satisfies 8n + 1 constraint (e.g. 49, 73, 97, 121, 161).
4. Positive prompt contains a `Music: <style>` line.
5. CFG input not modified (distilled model requires CFG=1).
6. Model paths resolved via `check_model` and patched into loader nodes `103`, `126`.

If all pass → `signal_workflow_ready(workflow_path)`.

---

## Common patch bundle

```json
[
  {"node_id": "31", "input_name": "image", "value": "high_view_classic_car.png"},
  {"node_id": "39", "input_name": "image", "value": "low_view_classic_car.png"},
  {"node_id": "98", "input_name": "value", "value": 720},
  {"node_id": "100", "input_name": "noise_seed", "value": 315253765879496},
  {"node_id": "102", "input_name": "value", "value": 121},
  {"node_id": "112", "input_name": "text", "value": "blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, excessive noise, grainy texture, poor lighting, flickering, motion blur, distorted proportions, unnatural skin tones, deformed facial features, asymmetrical face, missing facial features, extra limbs, disfigured hands, wrong hand count, artifacts around text, unreadable text on shirt or hat, incorrect lettering on cap (\u201cPNTR\u201d), incorrect t-shirt slogan (\u201cJUST DO IT\u201d), missing microphone, misplaced microphone, inconsistent perspective, camera shake, incorrect depth of field, background too sharp, background clutter, distracting reflections, harsh shadows, inconsistent lighting direction, color banding, cartoonish rendering, 3D CGI look, unrealistic materials, uncanny valley effect, incorrect ethnicity, wrong gender, exaggerated expressions, smiling, laughing, exaggerated sadness, wrong gaze direction, eyes looking at camera, mismatched lip sync, silent or muted audio, distorted voice, robotic voice, echo, background noise, off-sync audio, missing sniff sounds, incorrect dialogue, added dialogue, repetitive speech, jittery movement, awkward pauses, incorrect timing, unnatural transitions, inconsistent framing, tilted camera, missing door or shelves, missing shallow depth of field, flat lighting, inconsistent tone, cinematic oversaturation, stylized filters, or AI artifacts."},
  {"node_id": "113", "input_name": "value", "value": 1280},
  {"node_id": "128", "input_name": "text", "value": "The camera move from a high position to a low position, keeping the character in the frame centered.\nMusic: Synthwave cyberpunk music with calm ambient synths and driving 80s beats."},
  {"node_id": "130", "input_name": "filename_prefix", "value": "AnimateDiff"},
  {"node_id": "130", "input_name": "format", "value": "video/h264-mp4"},
  {"node_id": "130", "input_name": "crf", "value": 19}
]
```

Send all patches in a single `patch_workflow` call.

---

## Troubleshooting

- **Model file missing** → Ensure `ltx-2.3-22b-distilled-fp8.safetensors` is available for nodes 103 and 126.
- **Out of Memory (OOM)** → Reduce the resolution values in nodes 98 or 113.
- **Incorrect CFG settings** → Do not modify node 116 which is required to be CFG=1.
- **Poor motion quality** → Verify that nodes 31 and 39 contain compatible start and end frames.
- **Sampler error** → Do not patch node 118 to maintain the manual sigma configuration.
- **No audio / silent output** → check positive prompt contains a `Music: <style>` line.
