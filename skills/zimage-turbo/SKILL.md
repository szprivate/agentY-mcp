---
name: zimage-turbo
description: "henever researcher selected a zimage-turbo template: Follow these detailed instructions to build and patch z-Image workflows according to the `brainbriefing` specifications."
allowed-tools: patch_workflow, check_model
---


# ALWAYS APPLY: z-Image Workflow Assembly Instructions
- use this exact configuration of CLiP and VAE models for any z-Image workflows:
  - CLIP: `qwen_3_4b.safetensors`
  - VAE: `ae.safetensors` -- use this exact name for the safetensor file, do not add any prefixes or suffixes to the filename. 
  - Use the `check_model` tool to verify that the correct CLIP and VAE models are present in the system before proceeding with workflow assembly. If the required models are not found, report an error and halt the workflow assembly process.
- IMPORTANT: do not deviate from the specified CLIP and VAE models for z-Image workflows! 
