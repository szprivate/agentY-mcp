---
name: image-z-image-turbo-fun-union-controlnet
description: "Patch and validate image editing workflows. Activate when brainbriefing template name contains 'image_z_image_turbo_fun_union_controlnet'. Output, Input images / video, Sampler params, Prompts, Canny, CLIPLoader, ModelPatchLoader, VAEDecode, ModelSamplingAuraFlow, ConditioningZeroOut, QwenImageDiffsynthControlnet, EmptySD3LatentImage, GetImageSize"
allowed-tools: patch_workflow check_model
---

# Image Z Image Turbo Fun Union Controlnet workflow assembly

Assembles and validates image editing workflows using z_image_turbo_bf16.

---

## Workflow shape

- **Inputs:** image
- **Output:** image (PNG/WebP)
- **Model:** `z_image_turbo_bf16.safetensors`
- **Sampler:** res_multistep 9 steps, simple scheduler
- **CFG:** 1 (distilled — never raise)

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
| `58` | `LoadImage` (Load Image) | `image` | Do not touch node `57` — reads from this automatically. |

### Sampler params

| Node | Type | Input | Notes |
|---|---|---|---|
| `70:44` | `KSampler` (KSampler) | `seed` | Do not touch node `70:43` — reads from this automatically. |
| `70:44` | `KSampler` (KSampler) | `steps` | Do not touch node `70:43` — reads from this automatically. |
| `70:44` | `KSampler` (KSampler) | `cfg` | Do not touch node `70:43` — reads from this automatically. |
| `70:44` | `KSampler` (KSampler) | `sampler_name` | Do not touch node `70:43` — reads from this automatically. |
| `70:44` | `KSampler` (KSampler) | `scheduler` | Do not touch node `70:43` — reads from this automatically. |
| `70:44` | `KSampler` (KSampler) | `denoise` | Do not touch node `70:43` — reads from this automatically. |

### Prompts

| Node | Type | Input | Notes |
|---|---|---|---|
| `70:45` | `CLIPTextEncode` (CLIP Text Encode (Prompt)) | `text` | Do not touch node `70:42` — reads from this automatically. |

Always upload input files via `upload_image` before patching.


---

## DO NOT TOUCH — these nodes are fixed

### Model loaders

| Node | Reason |
|---|---|
| `70:46` `UNETLoader` (Load Diffusion Model) | Loads `z_image_turbo_bf16.safetensors` — swap not safe without full reconfig. |
| `70:40` `VAELoader` (Load VAE) | Loads `ae.safetensors` — swap not safe without full reconfig. |

Use `check_model` to verify each file is present locally and resolve its full path
before patching the node. Missing models are handled upstream by the Researcher
(HuggingFace download) — the Brain's job is path resolution, not availability checking.

### Locked structural nodes

| Node | Reason |
|---|---|
| `57` `Canny` (Canny) | Structural node — do not patch. |
| `70:39` `CLIPLoader` (Load CLIP) | Structural node — do not patch. |
| `70:64` `ModelPatchLoader` (ModelPatchLoader) | Structural node — do not patch. |
| `70:43` `VAEDecode` (VAE Decode) | Structural node — do not patch. |
| `70:47` `ModelSamplingAuraFlow` (ModelSamplingAuraFlow) | Structural node — do not patch. |
| `70:42` `ConditioningZeroOut` (ConditioningZeroOut) | Conditioning node — do not patch. |
| `70:60` `QwenImageDiffsynthControlnet` (QwenImageDiffsynthControlnet) | Structural node — do not patch. |
| `70:41` `EmptySD3LatentImage` (EmptySD3LatentImage) | Structural node — do not patch. |
| `70:69` `GetImageSize` (Get Image Size) | Auto-driven by resolution primitives. |

---

## Validation checklist

1. Image inputs uploaded and patched into nodes `58`.
2. Positive and negative prompt nodes patched with user brief text.
3. CFG input not modified (distilled model requires CFG=1).
4. Model paths resolved via `check_model` and patched into loader nodes `70:46`, `70:40`.

If all pass → `signal_workflow_ready(workflow_path)`.

---

## Common patch bundle

```json
[
  {"node_id": "9", "input_name": "filename_prefix", "value": "z-image-turbo"},
  {"node_id": "58", "input_name": "image", "value": "image_z_image_turbo_fun_union_controlnet_input_image.png"},
  {"node_id": "70:44", "input_name": "seed", "value": 582911328872997},
  {"node_id": "70:44", "input_name": "steps", "value": 9},
  {"node_id": "70:44", "input_name": "cfg", "value": 1},
  {"node_id": "70:44", "input_name": "sampler_name", "value": "res_multistep"},
  {"node_id": "70:44", "input_name": "scheduler", "value": "simple"},
  {"node_id": "70:44", "input_name": "denoise", "value": 1},
  {"node_id": "70:45", "input_name": "text", "value": "Realistic photo, close-up of a latina model peeking through pine branches, dappled sunlight on her face, natural, moody, smooth skin, a little bit film grain.\n"}
]
```

Send all patches in a single `patch_workflow` call.

---

## Troubleshooting

- **Model missing** → Ensure 'z_image_turbo_bf16.safetensors' is available for UNETLoader (70:46).
- **OOM error** → Reduce resolution in LoadImage (58) or decrease steps in KSampler (70:44).
- **CFG mismatch** → Verify CFG is set to 1 in KSampler (70:44) to satisfy workflow constraints.
- **ControlNet failure** → Check Canny (57) and QwenImageDiffsynthControlnet (70:60) node connectivity.
- **Prompt error** → Validate the text input in CLIP Text Encode (70:45).
