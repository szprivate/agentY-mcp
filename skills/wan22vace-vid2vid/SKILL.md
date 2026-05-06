---
name: wan22vace-vid2vid
description: "Patch and validate video-to-video workflows. Activate when brainbriefing template name contains 'Wan22Vace_VID2VID'. This workflow implements local video-to-video via Wan 2.2 VACE to apply the style of reference images to a control video while preserving motion consistency, with patchable groups for Sampler params, Prompts, LoRA, and Input images / video, and locked categories for structural, sampling, and model loading nodes."
allowed-tools: patch_workflow check_model
---

# Wan22Vace Vid2Vid workflow assembly

Assembles and validates image editing workflows using the configured model.

---

## Workflow shape

- **Inputs:** image
- **Output:** unknown
- **Model:** N/A
- **Sampler:** euler ['329', 0] steps, beta scheduler
- **CFG:** 1 (distilled — never raise)

---

## Patchable nodes — the ONLY things you may change

All patches go through `patch_workflow({node_id, input_name, value})`.

### Sampler params

| Node | Type | Input | Notes |
|---|---|---|---|
| `253` | `KSamplerAdvanced` (KSampler (Advanced)) | `steps` |  |
| `253` | `KSamplerAdvanced` (KSampler (Advanced)) | `cfg` |  |
| `253` | `KSamplerAdvanced` (KSampler (Advanced)) | `sampler_name` |  |
| `253` | `KSamplerAdvanced` (KSampler (Advanced)) | `scheduler` |  |
| `300` | `KSamplerAdvanced` (KSampler (Advanced)) | `steps` | Do not touch node `301` — reads from this automatically. |
| `300` | `KSamplerAdvanced` (KSampler (Advanced)) | `cfg` | Do not touch node `301` — reads from this automatically. |
| `300` | `KSamplerAdvanced` (KSampler (Advanced)) | `sampler_name` | Do not touch node `301` — reads from this automatically. |
| `300` | `KSamplerAdvanced` (KSampler (Advanced)) | `scheduler` | Do not touch node `301` — reads from this automatically. |

### Prompts

| Node | Type | Input | Notes |
|---|---|---|---|
| `258` | `CLIPTextEncode` (CLIP Text Encode (Negative Prompt)) | `text` | Do not touch node `296` — reads from this automatically. |
| `290` | `CLIPTextEncode` (CLIP Text Encode (Positive Prompt)) | `text` | Do not touch node `296` — reads from this automatically. |

### LoRA

| Node | Type | Input | Notes |
|---|---|---|---|
| `731` | `LoraLoaderModelOnly` (Load LoRA) | `lora_name` | Do not touch node `582` — reads from this automatically. |
| `731` | `LoraLoaderModelOnly` (Load LoRA) | `strength_model` | Do not touch node `582` — reads from this automatically. |
| `732` | `LoraLoaderModelOnly` (Load LoRA) | `lora_name` | Do not touch node `583` — reads from this automatically. |
| `732` | `LoraLoaderModelOnly` (Load LoRA) | `strength_model` | Do not touch node `583` — reads from this automatically. |

### Input images / video

| Node | Type | Input | Notes |
|---|---|---|---|
| `995` | `LoadImage` (Load Image) | `image` | Do not touch node `943` — reads from this automatically. |
| `996` | `LoadImage` (Load Image) | `image` | Do not touch node `943` — reads from this automatically. |

Always upload input files via `upload_image` before patching.


---

## DO NOT TOUCH — these nodes are fixed

### Model loaders

| Node | Reason |
|---|---|
| `585` `VAELoader` (Load VAE) | Loads `WAN21\wan_2.1_vae.safetensors` — swap not safe without full reconfig. |

Use `check_model` to verify each file is present locally and resolve its full path
before patching the node. Missing models are handled upstream by the Researcher
(HuggingFace download) — the Brain's job is path resolution, not availability checking.

### Locked structural nodes

| Node | Reason |
|---|---|
| `280` `VAEDecode` (VAE Decode) | Structural node — do not patch. |
| `296` `WanVaceToVideo` (WanVaceToVideo) | Structural node — do not patch. |
| `301` `TrimVideoLatent` (TrimVideoLatent) | Structural node — do not patch. |
| `329` `Int` (STEPS) | Structural node — do not patch. |
| `330` `easy mathInt` (START / END STEP 01) | Structural node — do not patch. |
| `582` `ModelSamplingSD3` (ModelSamplingSD3) | Structural node — do not patch. |
| `583` `ModelSamplingSD3` (ModelSamplingSD3) | Structural node — do not patch. |
| `584` `DiffusionModelSelector` (Diffusion Model Selector) | Structural node — do not patch. |
| `586` `CLIPLoader` (Load CLIP) | Structural node — do not patch. |
| `590` `DiffusionModelSelector` (Diffusion Model Selector) | Structural node — do not patch. |
| `593` `DiffusionModelLoaderKJ` (Diffusion Model Loader KJ) | Structural node — do not patch. |
| `594` `DiffusionModelLoaderKJ` (Diffusion Model Loader KJ) | Structural node — do not patch. |
| `719` `bEpicReformat` (bEpic Nuke Reformat) | Structural node — do not patch. |
| `943` `ImageStitch` (Image Stitch) | Structural node — do not patch. |
| `981` `bepicVaceKeyframeReplacer` (bEpic WAN VACE keyframe generator) | Structural node — do not patch. |
| `985` `BatchImagesNode` (Batch Images) | Structural node — do not patch. |
| `997` `LoadVideo` (Load Video) | Structural node — do not patch. |
| `998` `GetVideoComponents` (Get Video Components) | Structural node — do not patch. |
| `999` `SaveVideo` (Save Video) | Structural node — do not patch. |
| `1000` `CreateVideo` (Create Video) | Structural node — do not patch. |

---

## Validation checklist

1. Image inputs uploaded and patched into nodes `995`, `996`.
2. Positive and negative prompt nodes patched with user brief text.
3. CFG input not modified (distilled model requires CFG=1).
4. LoRA files verified via `check_model`: `WAN22\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank256_bf16.safetensors`, `WAN22\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank256_bf16.safetensors`.
5. Model paths resolved via `check_model` and patched into loader nodes `585`.

If all pass → `signal_workflow_ready(workflow_path)`.

---

## Common patch bundle

```json
[
  {"node_id": "253", "input_name": "steps", "value": "<value>"},
  {"node_id": "253", "input_name": "cfg", "value": 1},
  {"node_id": "253", "input_name": "sampler_name", "value": "euler"},
  {"node_id": "253", "input_name": "scheduler", "value": "beta"},
  {"node_id": "258", "input_name": "text", "value": "Vibrant colors, overexposure, static, blurred details, subtitles, style, artwork, painting, still image, overall grayness, worst quality, low quality, JPEG compression residue, ugly, mutilated, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, malformed limbs, fused fingers, still image, cluttered background, three legs, crowded background, walking backwards"},
  {"node_id": "290", "input_name": "text", "value": ""},
  {"node_id": "300", "input_name": "steps", "value": "<value>"},
  {"node_id": "300", "input_name": "cfg", "value": 1},
  {"node_id": "300", "input_name": "sampler_name", "value": "euler"},
  {"node_id": "300", "input_name": "scheduler", "value": "beta"},
  {"node_id": "731", "input_name": "lora_name", "value": "WAN22\\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank256_bf16.safetensors"},
  {"node_id": "731", "input_name": "strength_model", "value": 1},
  {"node_id": "732", "input_name": "lora_name", "value": "WAN22\\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank256_bf16.safetensors"},
  {"node_id": "732", "input_name": "strength_model", "value": 1},
  {"node_id": "995", "input_name": "image", "value": "2875b7cd-5300-462d-8db2-59aac56995c1.png"},
  {"node_id": "996", "input_name": "image", "value": "2875b7cd-5300-462d-8db2-59aac56995c1.png"}
]
```

Send all patches in a single `patch_workflow` call.

---

## Troubleshooting

- **VAE missing** → Ensure `wan_2.1_vae.safetensors` is correctly loaded in node 585.
- **Out of Memory (OOM)** → Reduce resolution in nodes 995 or 996, or decrease steps in nodes 253 and 300.
- **CFG error** → Verify CFG is set to 1 in nodes 253 and 300 to satisfy distillation constraints.
- **LoRA error** → Confirm the `lightx2v` LoRA file is present for nodes 731 and 732.
- **Motion inconsistency** → Check that the reference images in nodes 995 and 996 align with the control video content.
