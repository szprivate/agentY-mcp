---
name: image-flux2-klein-image-edit-9b-distilled
description: "Patch and validate [image] workflows. Activate when brainbriefing template name contains 'image_flux2_klein_image_edit_9b_distilled'. Includes patchable groups for Output, Input images / video, Seed, and Prompts, and locked categories for Sampler recipe, Structural node, Conditioning node, and Auto-driven nodes."
allowed-tools: patch_workflow check_model
---

# Image Flux2 Klein Image Edit 9B Distilled workflow assembly

Assembles and validates image editing workflows using Flux.

---

## Workflow shape

- **Inputs:** image
- **Output:** image (PNG/WebP)
- **Model:** `flux-2-klein-9b-fp8.safetensors`
- **Sampler:** N/A
- **CFG:** ? (distilled — never raise)

---

## Patchable nodes — the ONLY things you may change

All patches go through `patch_workflow({node_id, input_name, value})`.

### Output

| Node | Type | Input | Notes |
|---|---|---|---|
| `9` | `SaveImage` (Save Image) | `filename_prefix` |  |

### Input images / video

| Node | Type | Input | Notes |
|---|---|---|---|
| `76` | `LoadImage` (Load Image) | `image` | Do not touch node `75:80` — reads from this automatically. |

### Seed

| Node | Type | Input | Notes |
|---|---|---|---|
| `75:73` | `RandomNoise` (RandomNoise) | `noise_seed` | Do not touch node `75:64` — reads from this automatically. |

### Prompts

| Node | Type | Input | Notes |
|---|---|---|---|
| `75:74` | `CLIPTextEncode` (CLIP Text Encode (Positive Prompt)) | `text` | Do not touch node `75:82` — reads from this automatically. |

Always upload input files via `upload_image` before patching.


---

## DO NOT TOUCH — these nodes are fixed

### Model loaders

| Node | Reason |
|---|---|
| `75:70` `UNETLoader` (Load Diffusion Model) | Loads `flux-2-klein-9b-fp8.safetensors` — swap not safe without full reconfig. |
| `75:72` `VAELoader` (Load VAE) | Loads `flux2-vae.safetensors` — swap not safe without full reconfig. |

Use `check_model` to verify each file is present locally and resolve its full path
before patching the node. Missing models are handled upstream by the Researcher
(HuggingFace download) — the Brain's job is path resolution, not availability checking.

### Locked structural nodes

| Node | Reason |
|---|---|
| `75:61` `KSamplerSelect` (KSamplerSelect) | Sampler recipe — do not change. |
| `75:64` `SamplerCustomAdvanced` (SamplerCustomAdvanced) | Sampler recipe — do not change. |
| `75:65` `VAEDecode` (VAE Decode) | Structural node — do not patch. |
| `75:71` `CLIPLoader` (Load CLIP) | Structural node — do not patch. |
| `75:66` `EmptyFlux2LatentImage` (Empty Flux 2 Latent) | Structural node — do not patch. |
| `75:80` `ImageScaleToTotalPixels` (ImageScaleToTotalPixels) | Structural node — do not patch. |
| `75:63` `CFGGuider` (CFGGuider) | Sampler recipe — do not change. |
| `75:62` `Flux2Scheduler` (Flux2Scheduler) | Structural node — do not patch. |
| `75:82` `ConditioningZeroOut` (ConditioningZeroOut) | Conditioning node — do not patch. |
| `75:99` `GetImageSize` (Get Image Size) | Auto-driven by resolution primitives. |
| `75:79:100` `ReferenceLatent` (ReferenceLatent) | Structural node — do not patch. |
| `75:79:78` `VAEEncode` (VAE Encode) | Structural node — do not patch. |
| `75:79:77` `ReferenceLatent` (ReferenceLatent) | Structural node — do not patch. |

---

## Validation checklist

1. Image inputs uploaded and patched into nodes `76`.
2. Positive and negative prompt nodes patched with user brief text.
3. CFG input not modified (distilled model requires CFG=1).
4. Model paths resolved via `check_model` and patched into loader nodes `75:70`, `75:72`.

If all pass → `signal_workflow_ready(workflow_path)`.

---

## Common patch bundle

```json
[
  {"node_id": "9", "input_name": "filename_prefix", "value": "Flux2-Klein"},
  {"node_id": "76", "input_name": "image", "value": "bold_outfit_woman.jpeg"},
  {"node_id": "75:73", "input_name": "noise_seed", "value": 137120342660015},
  {"node_id": "75:74", "input_name": "text", "value": "Replace the background with a quiet coastal cliff at overcast sunset. Remove all buildings and streets. Add wind-shaped grass and a distant ocean horizon. Keep the subject\u2019s pose and framing unchanged."}
]
```

Send all patches in a single `patch_workflow` call.

---

## Troubleshooting

- **Model missing** → Ensure 'flux-2-klein-9b-fp8.safetensors' is present for node 75:70.
- **Out of Memory (OOM)** → Decrease resolution in node 75:80 or use a smaller model in node 75:70.
- **CFG constraint violation** → Ensure node 75:63 is set to 1 as required.
- **Bad output quality** → Refine the prompt in node 75:74 or check the source image in node 76.
