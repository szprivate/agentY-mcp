---
name: image-z-image-turbo
description: "Patch and validate text-to-image workflows. Activate when brainbriefing template name contains 'image_z_image_turbo'. Output, Prompts, Sampler params, CLIPLoader, ConditioningZeroOut, VAEDecode, EmptySD3LatentImage, ModelSamplingAuraFlow."
allowed-tools: patch_workflow check_model
---

# Image Z Image Turbo workflow assembly

Assembles and validates text-to-image workflows using z_image_turbo_bf16.

---

## Workflow shape

- **Inputs:** text only
- **Output:** image (PNG/WebP)
- **Model:** `z_image_turbo_bf16.safetensors`
- **Sampler:** res_multistep 8 steps, simple scheduler
- **CFG:** 1 (distilled — never raise)

---

## Patchable nodes — the ONLY things you may change

All patches go through `patch_workflow({node_id, input_name, value})`.

### Output

| Node | Type | Input | Notes |
|---|---|---|---|
| `9` | `SaveImage` (Save Image) | `filename_prefix` |  |

### Prompts

| Node | Type | Input | Notes |
|---|---|---|---|
| `57:27` | `CLIPTextEncode` (CLIP Text Encode (Prompt)) | `text` | Do not touch node `57:33` — reads from this automatically. |

### Sampler params

| Node | Type | Input | Notes |
|---|---|---|---|
| `57:3` | `KSampler` (KSampler) | `seed` | Do not touch node `57:8` — reads from this automatically. |
| `57:3` | `KSampler` (KSampler) | `steps` | Do not touch node `57:8` — reads from this automatically. |
| `57:3` | `KSampler` (KSampler) | `cfg` | Do not touch node `57:8` — reads from this automatically. |
| `57:3` | `KSampler` (KSampler) | `sampler_name` | Do not touch node `57:8` — reads from this automatically. |
| `57:3` | `KSampler` (KSampler) | `scheduler` | Do not touch node `57:8` — reads from this automatically. |
| `57:3` | `KSampler` (KSampler) | `denoise` | Do not touch node `57:8` — reads from this automatically. |


---

## DO NOT TOUCH — these nodes are fixed

### Model loaders

| Node | Reason |
|---|---|
| `57:29` `VAELoader` (Load VAE) | Loads `ae.safetensors` — swap not safe without full reconfig. |
| `57:28` `UNETLoader` (Load Diffusion Model) | Loads `z_image_turbo_bf16.safetensors` — swap not safe without full reconfig. |

Use `check_model` to verify each file is present locally and resolve its full path
before patching the node. Missing models are handled upstream by the Researcher
(HuggingFace download) — the Brain's job is path resolution, not availability checking.

### Locked structural nodes

| Node | Reason |
|---|---|
| `57:30` `CLIPLoader` (Load CLIP) | Structural node — do not patch. |
| `57:33` `ConditioningZeroOut` (ConditioningZeroOut) | Conditioning node — do not patch. |
| `57:8` `VAEDecode` (VAE Decode) | Structural node — do not patch. |
| `57:13` `EmptySD3LatentImage` (EmptySD3LatentImage) | Structural node — do not patch. |
| `57:11` `ModelSamplingAuraFlow` (ModelSamplingAuraFlow) | Structural node — do not patch. |

---

## Validation checklist

1. Positive and negative prompt nodes patched with user brief text.
2. CFG input not modified (distilled model requires CFG=1).
3. Model paths resolved via `check_model` and patched into loader nodes `57:29`, `57:28`.

If all pass → `signal_workflow_ready(workflow_path)`.

---

## Common patch bundle

```json
[
  {"node_id": "9", "input_name": "filename_prefix", "value": "z-image-turbo"},
  {"node_id": "57:27", "input_name": "text", "value": "Latina female with thick wavy hair, harbor boats and pastel houses behind. Breezy seaside light, warm tones, cinematic close-up. "},
  {"node_id": "57:3", "input_name": "seed", "value": 0},
  {"node_id": "57:3", "input_name": "steps", "value": 8},
  {"node_id": "57:3", "input_name": "cfg", "value": 1},
  {"node_id": "57:3", "input_name": "sampler_name", "value": "res_multistep"},
  {"node_id": "57:3", "input_name": "scheduler", "value": "simple"},
  {"node_id": "57:3", "input_name": "denoise", "value": 1}
]
```

Send all patches in a single `patch_workflow` call.

---

## Troubleshooting

- **Model missing** → Ensure 'z_image_turbo_bf16.safetensors' is available in the models directory.
- **Out of Memory (OOM)** → Reduce sampling steps or resolution at node 57:3.
- **CFG constraint violation** → Verify that CFG is set to 1 at node 57:3.
- **Poor image quality** → Check prompt text at node 57:27 or sampler parameters at node 57:3.
