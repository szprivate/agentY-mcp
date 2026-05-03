---
name: video-ltx2-3-i2v
description: "Patch and validate [image-to-video] workflows. Activate when brainbriefing template name contains 'video_ltx2_3_i2v'. Patchable categories include Input images / video, Output, Seed, Resolution, Length / FPS, LoRA, and Prompts, and locked categories include Sampler recipe, Structural node, Math passthrough, Conditioning node, Pure wiring, and Auto-driven."
allowed-tools: patch_workflow check_model
---

# Video Ltx2 3 I2V workflow assembly

Assembles and validates image-to-video workflows using LTX-Video.

---

## Workflow shape

- **Inputs:** image
- **Output:** video (VHS container)
- **Model:** `ltx-2.3-22b-dev-fp8.safetensors`, `ltx-2.3-spatial-upscaler-x2-1.1.safetensors`, `ltx-2.3-22b-dev-fp8.safetensors`
- **Sampler:** N/A
- **CFG:** ? (distilled — never raise)

---

## Patchable nodes — the ONLY things you may change

All patches go through `patch_workflow({node_id, input_name, value})`.

### Input images / video

| Node | Type | Input | Notes |
|---|---|---|---|
| `269` | `LoadImage` (Load Image) | `image` | Do not touch node `267:238`, `267:274` — reads from this automatically. |

### Output

| Node | Type | Input | Notes |
|---|---|---|---|
| `277` | `VHS_VideoCombine` (Video Combine 🎥🅥🅗🅢) | `filename_prefix` |  |
| `277` | `VHS_VideoCombine` (Video Combine 🎥🅥🅗🅢) | `format` |  |
| `277` | `VHS_VideoCombine` (Video Combine 🎥🅥🅗🅢) | `crf` |  |

### Seed

| Node | Type | Input | Notes |
|---|---|---|---|
| `267:216` | `RandomNoise` (RandomNoise) | `noise_seed` | Do not touch node `267:219` — reads from this automatically. |
| `267:237` | `RandomNoise` (RandomNoise) | `noise_seed` | Do not touch node `267:215` — reads from this automatically. |

### Resolution

| Node | Type | Input | Notes |
|---|---|---|---|
| `267:257` | `PrimitiveInt` (Width) | `value` | Do not touch node `267:256`, `267:238` — reads from this automatically. |
| `267:258` | `PrimitiveInt` (Height) | `value` | Do not touch node `267:238`, `267:259` — reads from this automatically. |

### Length / FPS

| Node | Type | Input | Notes |
|---|---|---|---|
| `267:225` | `PrimitiveInt` (Length) | `value` | Do not touch node `267:214`, `267:228` — reads from this automatically. |

### LoRA

| Node | Type | Input | Notes |
|---|---|---|---|
| `267:232` | `LoraLoaderModelOnly` (Load LoRA) | `lora_name` | Do not touch node `267:231`, `267:213` — reads from this automatically. |
| `267:232` | `LoraLoaderModelOnly` (Load LoRA) | `strength_model` | Do not touch node `267:231`, `267:213` — reads from this automatically. |
| `267:272` | `LoraLoader` (Load LoRA (Model and CLIP)) | `lora_name` | Do not touch node `267:274` — reads from this automatically. |
| `267:272` | `LoraLoader` (Load LoRA (Model and CLIP)) | `strength_model` | Do not touch node `267:274` — reads from this automatically. |
| `267:272` | `LoraLoader` (Load LoRA (Model and CLIP)) | `strength_clip` | Do not touch node `267:274` — reads from this automatically. |

### Prompts

| Node | Type | Input | Notes |
|---|---|---|---|
| `267:247` | `CLIPTextEncode` (CLIP Text Encode (Prompt)) | `text` | Must include a `Music: <style>` line — parsed by the audio decoder. Do not touch node `267:239` — reads from this automatically. |
| `267:240` | `CLIPTextEncode` (CLIP Text Encode (Prompt)) | `text` | Must include a `Music: <style>` line — parsed by the audio decoder. Do not touch node `267:239` — reads from this automatically. |

Always upload input files via `upload_image` before patching.


---

## DO NOT TOUCH — these nodes are fixed

### Model loaders

| Node | Reason |
|---|---|
| `267:221` `LTXVAudioVAELoader` (LTXV Audio VAE Loader) | Loads `ltx-2.3-22b-dev-fp8.safetensors` — swap not safe without full reconfig. |
| `267:233` `LatentUpscaleModelLoader` (Load Latent Upscale Model) | Loads `ltx-2.3-spatial-upscaler-x2-1.1.safetensors` — swap not safe without full reconfig. |
| `267:243` `LTXAVTextEncoderLoader` (LTXV Audio Text Encoder Loader) | Loads `gemma_3_12B_it_fp4_mixed.safetensors`, `ltx-2.3-22b-dev-fp8.safetensors` — swap not safe without full reconfig. |

Use `check_model` to verify each file is present locally and resolve its full path
before patching the node. Missing models are handled upstream by the Researcher
(HuggingFace download) — the Brain's job is path resolution, not availability checking.

### Locked structural nodes

| Node | Reason |
|---|---|
| `276` `GetVideoComponents` (Get Video Components) | Structural node — do not patch. |
| `267:246` `KSamplerSelect` (KSamplerSelect) | Sampler recipe — do not change. |
| `267:211` `ManualSigmas` (ManualSigmas) | Checkpoint-matched sigma schedule — do not change. |
| `267:209` `KSamplerSelect` (KSamplerSelect) | Sampler recipe — do not change. |
| `267:201` `PrimitiveBoolean` (Switch to Text to Video?) | Structural node — do not patch. |
| `267:252` `ManualSigmas` (ManualSigmas) | Checkpoint-matched sigma schedule — do not change. |
| `267:236` `CheckpointLoaderSimple` (Load Checkpoint) | Structural node — do not patch. |
| `267:266` `PrimitiveStringMultiline` (Prompt) | Structural node — do not patch. |
| `267:260` `PrimitiveInt` (Frame Rate) | Structural node — do not patch. |
| `267:256` `ComfyMathExpression` (Math Expression) | Math passthrough — reads from upstream primitive. |
| `267:261` `ComfyMathExpression` (Math Expression) | Math passthrough — reads from upstream primitive. |
| `267:238` `ResizeImageMaskNode` (Resize Image/Mask) | Auto-driven by resolution primitives. |
| `267:259` `ComfyMathExpression` (Math Expression) | Math passthrough — reads from upstream primitive. |
| `267:274` `TextGenerateLTX2Prompt` (TextGenerateLTX2Prompt) | Structural node — do not patch. |
| `267:214` `LTXVEmptyLatentAudio` (LTXV Empty Latent Audio) | Structural node — do not patch. |
| `267:235` `ResizeImagesByLongerEdge` (Resize Images by Longer Edge) | Auto-driven by resolution primitives. |
| `267:228` `EmptyLTXVLatentVideo` (EmptyLTXVLatentVideo) | Structural node — do not patch. |
| `267:275` `PreviewAny` (Preview as Text) | Structural node — do not patch. |
| `267:248` `LTXVPreprocess` (LTXVPreprocess) | Auto-driven by resolution primitives. |
| `267:239` `LTXVConditioning` (LTXVConditioning) | Conditioning node — do not patch. |
| `267:249` `LTXVImgToVideoInplace` (LTXVImgToVideoInplace) | Structural node — do not patch. |
| `267:231` `CFGGuider` (CFGGuider) | Sampler recipe — do not change. |
| `267:222` `LTXVConcatAVLatent` (LTXVConcatAVLatent) | Pure wiring — do not patch. |
| `267:215` `SamplerCustomAdvanced` (SamplerCustomAdvanced) | Sampler recipe — do not change. |
| `267:217` `LTXVSeparateAVLatent` (LTXVSeparateAVLatent) | Pure wiring — do not patch. |
| `267:212` `LTXVCropGuides` (LTXVCropGuides) | Pure wiring — do not patch. |
| `267:253` `LTXVLatentUpsampler` (LTXVLatentUpsampler) | Structural node — do not patch. |
| `267:213` `CFGGuider` (CFGGuider) | Sampler recipe — do not change. |
| `267:230` `LTXVImgToVideoInplace` (LTXVImgToVideoInplace) | Structural node — do not patch. |
| `267:229` `LTXVConcatAVLatent` (LTXVConcatAVLatent) | Pure wiring — do not patch. |
| `267:219` `SamplerCustomAdvanced` (SamplerCustomAdvanced) | Sampler recipe — do not change. |
| `267:218` `LTXVSeparateAVLatent` (LTXVSeparateAVLatent) | Pure wiring — do not patch. |
| `267:251` `VAEDecodeTiled` (VAE Decode (Tiled)) | Structural node — do not patch. |
| `267:220` `LTXVAudioVAEDecode` (LTXV Audio VAE Decode) | Structural node — do not patch. |
| `267:242` `CreateVideo` (Create Video) | Structural node — do not patch. |

---

## Validation checklist

1. Image inputs uploaded and patched into nodes `269`.
2. Positive and negative prompt nodes patched with user brief text.
3. Positive prompt contains a `Music: <style>` line.
4. CFG input not modified (distilled model requires CFG=1).
5. LoRA files verified via `check_model`: `ltx-2.3-22b-distilled-lora-384.safetensors`, `gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors`.
6. Model paths resolved via `check_model` and patched into loader nodes `267:221`, `267:233`, `267:243`.

If all pass → `signal_workflow_ready(workflow_path)`.

---

## Common patch bundle

```json
[
  {"node_id": "269", "input_name": "image", "value": "egyptian_queen.png"},
  {"node_id": "277", "input_name": "filename_prefix", "value": "AnimateDiff"},
  {"node_id": "277", "input_name": "format", "value": "video/h264-mp4"},
  {"node_id": "277", "input_name": "crf", "value": 19},
  {"node_id": "267:216", "input_name": "noise_seed", "value": 42},
  {"node_id": "267:237", "input_name": "noise_seed", "value": 723381549937839},
  {"node_id": "267:257", "input_name": "value", "value": 1280},
  {"node_id": "267:225", "input_name": "value", "value": 121},
  {"node_id": "267:258", "input_name": "value", "value": 720},
  {"node_id": "267:232", "input_name": "lora_name", "value": "ltx-2.3-22b-distilled-lora-384.safetensors"},
  {"node_id": "267:232", "input_name": "strength_model", "value": 0.5},
  {"node_id": "267:272", "input_name": "lora_name", "value": "gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors"},
  {"node_id": "267:272", "input_name": "strength_model", "value": 1},
  {"node_id": "267:272", "input_name": "strength_clip", "value": 1},
  {"node_id": "267:247", "input_name": "text", "value": "pc game, console game, video game, cartoon, childish, ugly"},
  {"node_id": "267:240", "input_name": "text", "value": "<value>"}
]
```

Send all patches in a single `patch_workflow` call.

---

## Troubleshooting

- **Model loading error** → Ensure ltx-2.3-22b-dev-fp8.safetensors is present in the models folder.
- **Out of Memory (OOM) error** → Reduce dimensions in 267:257 or 267:258.
- **Incorrect sampling behavior** → Check that manual sigmas at 267:211 and 267:252 are not altered.
- **Poor prompt adherence** → Re-evaluate the text in 267:247 or 267:240.
- **CFG-related sampling errors** → Verify that 267:231 and 267:213 remain as one-nodes.
- **No audio / silent output** → check positive prompt contains a `Music: <style>` line.
