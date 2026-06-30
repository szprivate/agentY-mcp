# Workflow recipe database  (task -> model -> node clusters)

- Tasks: 18 | task+model recipes: 40
- Self-contained: every recipe has user_intent + description + node clusters. No human annotation step.

# API / Partner Nodes - Image Edit  (`api_partner_nodes_image_edit`)  -  6 workflow(s), 4 model(s)

## API / Partner Nodes - Image Edit / Nano-Banana  (`api_partner_nodes_image_edit__nano_banana`)  -  3 workflow(s)  -  source: custom
- execution: api (API nodes: GeminiImage2Node, GeminiNanoBanana2, GeminiNode)
- when to use: Use to edit an existing image using Nano-Banana, Gemini.
- example request: "build an image workflow using Nano-Banana"
- description: API image editing/generation via Nano-Banana 2. Up to 6 reference images + text prompt -> 1 image output. Edits images while maintaining subject consistency, or uses references as style guides for new image generation. | API image editing/generation via Nano-Banana Pro (Gemini 3.0 Pro). 2 image inputs -> 1 image output. Studio-quality 4K generation and editing with enhanced text rendering and character consistency. | Local style transfer FOR FULL BODY SHOTS via Nano-Banana Pro (Gemini). 1 video (layout reference) + 7 images (style + hero elements) -> 2 image outputs. Transfers the style reference onto the first video frame while integrating the look of hero element references.
- member workflows:
    - imageEdit_nano_banana2
    - imageEdit_nano_banana_pro
    - styletransfer_NanoBananaPro
- node clusters (required structure):
    - output: SaveImage
- optional roles: VHS_LoadImagePath, BatchImagesNode, LoadImage, AILab_ImageToList, GeminiImage2Node, GeminiNanoBanana2, GeminiNode, ImageListToImageBatch, PreviewImage, VHS_LoadVideoPath, VHS_SelectImages, bEpicReformat

## API / Partner Nodes - Image Edit / Kling  (`api_partner_nodes_image_edit__kling`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: KlingOmniProImageNode)
- when to use: Use to generate an image using Kling.
- example request: "build an image workflow using Kling"
- description: Generate an image using Kling. Structurally it applies a sequence of node operations. Boundary inputs: IMAGE; outputs: IMAGE.
- member workflows:
    - api_kling_o3_image
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - output: SaveImage
    - other operations: ImageBatchMulti, KlingOmniProImageNode
- paired/multiple required: LoadImage x2

## API / Partner Nodes - Image Edit / Magnific  (`api_partner_nodes_image_edit__magnific`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: MagnificImageRelightNode)
- when to use: Use to relight an image using Magnific.
- example request: "build an image workflow using Magnific"
- description: API image relighting via Magnific. 1 source image + 1 lighting reference image -> 1 relit image output. Applies the lighting conditions from the reference onto the source image.
- member workflows:
    - api_magnific_image_relight
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - output: SaveImage
    - other operations: MagnificImageRelightNode
- paired/multiple required: LoadImage x2

## API / Partner Nodes - Image Edit / Seedream  (`api_partner_nodes_image_edit__seedream`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: ByteDanceSeedreamNode)
- when to use: Use to edit an existing image using Seedream.
- example request: "build an image workflow using Seedream"
- description: Edit an existing image using Seedream. Structurally it applies a sequence of node operations. Boundary inputs: IMAGE; outputs: IMAGE.
- member workflows:
    - api_bytedance_seedream_5_0_lite_image_edit
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - output: SaveImage
    - other operations: ByteDanceSeedreamNode, ImageBatchMulti
- paired/multiple required: LoadImage x2


# API / Partner Nodes - Text to Video  (`api_partner_nodes_text_to_video`)  -  5 workflow(s), 5 model(s)

## API / Partner Nodes - Text to Video / Generic  (`api_partner_nodes_text_to_video__generic`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: ByteDance2TextToVideoNode)
- when to use: Use to generate a video from a text prompt.
- example request: "build a video workflow"
- description: API text-to-video via Seedance 2.0 (ByteDance). Text prompt only -> 1 video output. Generates high-quality video from a text description using the Seedance 2.0 model.
- member workflows:
    - api_seedance2_t2v
- node clusters (required structure):
    - output: VHS_VideoCombine
    - other operations: ByteDance2TextToVideoNode, GetVideoComponents

## API / Partner Nodes - Text to Video / Kling  (`api_partner_nodes_text_to_video__kling`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: KlingVideoNode)
- when to use: Use to generate a video using Kling.
- example request: "build a video workflow using Kling"
- description: API multi-shot storyboard video via Kling 3.0 (kling-v3). 1 input image (start frame, LoadImage node) -> 1 video output (VHS_VideoCombine). Generates 1-6 sequential shots in a single generation: each shot has its own text prompt (max 512 chars) and duration set directly on the KlingVideoNode. Use for storyboards, scene sequences, and narrative clips with multiple camera cuts. Prompts go into multi_shot.storyboard_N_prompt inputs; multi_shot must match shot count exactly (e.g. '3 storyboards'). Aspect ratio defaults to 16:9, resolution to 720p - override only on explicit user request.
- member workflows:
    - Kling3_multiShot
- node clusters (required structure):
    - inputs: LoadImage
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, KlingVideoNode

## API / Partner Nodes - Text to Video / LTX-2  (`api_partner_nodes_text_to_video__ltx_2`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: LtxvApiTextToVideo)
- when to use: Use to generate a video from a text prompt using LTX-2.
- example request: "build a video workflow using LTX-2"
- description: Generate a video from a text prompt using LTX-2. Structurally it applies a sequence of node operations. Boundary inputs: VIDEO; outputs: AUDIO, IMAGE.
- member workflows:
    - api_ltxv_text_to_video
- node clusters (required structure):
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, LtxvApiTextToVideo

## API / Partner Nodes - Text to Video / Veo  (`api_partner_nodes_text_to_video__veo`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: Veo3VideoGenerationNode)
- when to use: Use to run a node graph using Veo.
- example request: "build a video workflow using Veo"
- description: Run a node graph using Veo. Structurally it applies a sequence of node operations. Boundary inputs: IMAGE; outputs: VIDEO.
- member workflows:
    - api_veo3
- node clusters (required structure):
    - inputs: LoadImage
    - output: SaveVideo
    - other operations: Veo3VideoGenerationNode

## API / Partner Nodes - Text to Video / WAN 2.6  (`api_partner_nodes_text_to_video__wan_2_6`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: WanTextToVideoApi)
- when to use: Use to generate a video from a text prompt using WAN 2.6.
- example request: "build a video workflow using WAN 2.6"
- description: API text-to-video via Wan 2.6. Text prompt only -> 1 video output. Generates 1080P video with enhanced quality, smoother motion, and improved prompt understanding.
- member workflows:
    - api_wan2_6_t2v
- node clusters (required structure):
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, WanTextToVideoApi


# Video to Video  (`video_to_video`)  -  5 workflow(s), 2 model(s)

## Video to Video / WAN VACE  (`video_to_video__wan_vace`)  -  4 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video from a text prompt using WAN VACE, WAN 2.2.
- example request: "build a video workflow using WAN VACE"
- description: [Local] image editing via Wan. 3 image inputs -> 1 image output. Performs advanced image-to-image editing and transformations.
- member workflows:
    - Wan22Vace_VID2VID
    - video_wan_vace_14B_ref2v
    - video_wan_vace_14B_v2v
    - video_wan_vace_outpainting
- node clusters (required structure):
    - model loading: CLIPLoader, VAELoader
    - conditioning: CLIPTextEncode (x2)
    - decoding: VAEDecode
    - other operations: CreateVideo, GetVideoComponents, ModelSamplingSD3, TrimVideoLatent, WanVaceToVideo
- paired/multiple required: CLIPTextEncode x2
- optional roles: DiffusionModelLoaderKJ, DiffusionModelSelector, KSamplerAdvanced, LoadImage, LoraLoaderModelOnly, PreviewImage, BatchImagesNode, ImagePadForOutpaint, ImageStitch, ImageToMask, Int, KSampler

## Video to Video / WAN 2.2  (`video_to_video__wan_2_2`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video guided by a control map (canny/depth/pose) using WAN 2.2.
- example request: "build a video workflow using WAN 2.2"
- description: Generate a video guided by a control map (canny/depth/pose) using WAN 2.2. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: IMAGE, VIDEO; outputs: AUDIO, IMAGE.
- member workflows:
    - video_wan2_2_14B_fun_control
- node clusters (required structure):
    - inputs: LoadImage, LoadVideo
    - model loading: CLIPLoader, UNETLoader (x2), VAELoader
    - conditioning: CLIPTextEncode (x2)
    - sampling: KSamplerAdvanced (x2)
    - decoding: VAEDecode
    - output: VHS_VideoCombine
    - other operations: CreateVideo, GetVideoComponents (x2), ModelSamplingSD3 (x2), Wan22FunControlToVideo
- paired/multiple required: CLIPTextEncode x2, GetVideoComponents x2, KSamplerAdvanced x2, ModelSamplingSD3 x2, UNETLoader x2


# API / Partner Nodes - Upscale  (`api_partner_nodes_upscale`)  -  4 workflow(s), 3 model(s)

## API / Partner Nodes - Upscale / Magnific  (`api_partner_nodes_upscale__magnific`)  -  2 workflow(s)  -  source: custom
- execution: api (API nodes: MagnificImageUpscalerCreativeNode, MagnificImageUpscalerPreciseV2Node)
- when to use: Use to upscale / enhance an image using Magnific.
- example request: "build an image workflow using Magnific"
- description: API creative image upscaling via Magnific. 1 image -> 1 upscaled image output. Supports up to 16x enlargement with creative detail enhancement. | API precise image upscaling via Magnific. 1 image -> 1 high-resolution image output. Upscales with strict detail preservation and enhanced sharpness.
- member workflows:
    - api_magnific_image_upscale_creative
    - api_magnific_image_upscale_precise
- node clusters (required structure):
    - inputs: LoadImage
    - output: SaveImage
- optional roles: MagnificImageUpscalerCreativeNode, MagnificImageUpscalerPreciseV2Node

## API / Partner Nodes - Upscale / Topaz  (`api_partner_nodes_upscale__topaz`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: TopazVideoEnhance)
- when to use: Use to increase a video's frame rate via interpolation using Topaz.
- example request: "build a video workflow using Topaz"
- description: API video upscaling via Topaz AI. 1 video -> 1 enhanced video output. Supports resolution upscaling (Starlight/Astra Fast model) and frame interpolation (apo-8 model).
- member workflows:
    - api_topaz_video_enhance
- node clusters (required structure):
    - inputs: LoadVideo
    - output: SaveVideo
    - other operations: TopazVideoEnhance

## API / Partner Nodes - Upscale / Z-Image  (`api_partner_nodes_upscale__z_image`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: TopazImageEnhance)
- when to use: Use to upscale / enhance an image using Topaz, Z-Image.
- example request: "build an image workflow using Topaz"
- description: API image enhancement/upscaling via Topaz Reimagine. 1 image -> 1 enhanced image output. Applies face enhancement and detail restoration for professional results.
- member workflows:
    - api_topaz_image_enhance
- node clusters (required structure):
    - inputs: LoadImage
    - output: SaveImage
    - other operations: TopazImageEnhance


# API / Partner Nodes - 3D  (`api_partner_nodes_3d`)  -  3 workflow(s), 1 model(s)

## API / Partner Nodes - 3D / Meshy  (`api_partner_nodes_3d__meshy`)  -  3 workflow(s)  -  source: custom
- execution: api (API nodes: MeshyImageToModelNode, MeshyMultiImageToModelNode, MeshyTextToModelNode)
- when to use: Use to generate a 3D model using Meshy.
- example request: "build a 3d workflow using Meshy"
- description: API image-to-3D via Meshy 6. 1 image -> 1 3D model output. Generates characters, objects, or mechanical parts with production-quality geometry and clean topology. | API multi-image-to-3D via Meshy 6. 3+ images -> 1 3D model output. More input views yield better detail capture, accurate proportions, and cleaner mesh structure. | API text-to-3D via Meshy 6. Text prompt only -> 1 3D model output. Creates characters, mechanical objects, or game-ready low-poly assets with refined geometry.
- member workflows:
    - api_meshy_image_to_model
    - api_meshy_multi_image_to_model
    - api_meshy_text_to_model
- node clusters (required structure):
    - other operations: SaveGLB (x2)
- paired/multiple required: SaveGLB x2
- optional roles: LoadImage, MeshyImageToModelNode, MeshyMultiImageToModelNode, MeshyTextToModelNode


# API / Partner Nodes - Image to Video  (`api_partner_nodes_image_to_video`)  -  3 workflow(s), 3 model(s)

## API / Partner Nodes - Image to Video / Kling  (`api_partner_nodes_image_to_video__kling`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: KlingOmniProImageToVideoNode)
- when to use: Use to generate a video from an input image using Kling.
- example request: "build a video workflow using Kling"
- description: API image-to-video via Kling O3 (Kling 3.0). 1 reference image (+ optional audio/text prompt) -> 1 video output. Generates character-consistent video with native audio output and precise storyboard control.
- member workflows:
    - api_kling_o3_i2v
- node clusters (required structure):
    - inputs: LoadImage
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, ImageBatchMulti, KlingOmniProImageToVideoNode

## API / Partner Nodes - Image to Video / LTX-2  (`api_partner_nodes_image_to_video__ltx_2`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: LtxvApiImageToVideo)
- when to use: Use to generate a video from an input image using LTX-2.
- example request: "build a video workflow using LTX-2"
- description: Generate a video from an input image using LTX-2. Structurally it applies a sequence of node operations. Boundary inputs: IMAGE; outputs: AUDIO, IMAGE.
- member workflows:
    - api_ltxv_image_to_video
- node clusters (required structure):
    - inputs: LoadImage
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, LtxvApiImageToVideo

## API / Partner Nodes - Image to Video / WAN 2.6  (`api_partner_nodes_image_to_video__wan_2_6`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: WanImageToVideoApi)
- when to use: Use to generate a video from an input image using WAN 2.6.
- example request: "build a video workflow using WAN 2.6"
- description: API image-to-video via Wan 2.6. 1 image -> 1 video output. Generates 1080P video with enhanced image quality, smoother motion, and natural movement.
- member workflows:
    - api_wan2_6_i2v
- node clusters (required structure):
    - inputs: LoadImage
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, WanImageToVideoApi


# First / Last Frame to Video  (`first_last_frame_to_video`)  -  3 workflow(s), 3 model(s)

## First / Last Frame to Video / LTX-2  (`first_last_frame_to_video__ltx_2`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video interpolating between a first and last frame using LTX-2.
- example request: "build a video workflow using LTX-2"
- description: Generate a video interpolating between a first and last frame using LTX-2. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; starts from an empty latent; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: IMAGE; outputs: AUDIO, IMAGE.
- member workflows:
    - video_ltx2_3_flf2v
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - model loading: CheckpointLoaderSimple, LTXVAudioVAELoader
    - conditioning: CFGGuider, CLIPTextEncode (x2), LTXAVTextEncoderLoader, LTXVConditioning, ManualSigmas
    - latent / canvas: LTXVEmptyLatentAudio
    - sampling: SamplerCustomAdvanced, SamplerEulerAncestral
    - decoding: LTXVAudioVAEDecode, VAEDecodeTiled
    - output: VHS_VideoCombine
    - other operations: ComfyMathExpression, CreateVideo, EmptyLTXVLatentVideo, GetImageSize, GetVideoComponents, LTXVAddGuide (x2), LTXVConcatAVLatent, LTXVCropGuides, LTXVPreprocess (x2), LTXVSeparateAVLatent, PrimitiveInt (x4), RandomNoise, ResizeImageMaskNode (x2)
- paired/multiple required: CLIPTextEncode x2, LTXVAddGuide x2, LTXVPreprocess x2, LoadImage x2, ResizeImageMaskNode x2

## First / Last Frame to Video / WAN 2.2  (`first_last_frame_to_video__wan_2_2`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video interpolating between a first and last frame using WAN 2.2.
- example request: "build a video workflow using WAN 2.2"
- description: Generate a video interpolating between a first and last frame using WAN 2.2. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: IMAGE; outputs: AUDIO, IMAGE.
- member workflows:
    - video_wan2_2_14B_flf2v
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - model loading: CLIPLoader, UNETLoader (x2), VAELoader
    - conditioning: CLIPTextEncode (x2)
    - sampling: KSamplerAdvanced (x2)
    - decoding: VAEDecode
    - output: VHS_VideoCombine
    - other operations: CreateVideo, GetVideoComponents, ModelSamplingSD3 (x2), WanFirstLastFrameToVideo
- paired/multiple required: CLIPTextEncode x2, KSamplerAdvanced x2, LoadImage x2, ModelSamplingSD3 x2, UNETLoader x2

## First / Last Frame to Video / WAN VACE  (`first_last_frame_to_video__wan_vace`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video interpolating between a first and last frame using WAN VACE.
- example request: "build a video workflow using WAN VACE"
- description: Generate a video interpolating between a first and last frame using WAN VACE. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: IMAGE, INT; outputs: IMAGE, MASK.
- member workflows:
    - video_wan_vace_flf2v
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - model loading: CLIPLoader, LoraLoader, UNETLoader, VAELoader
    - conditioning: CLIPTextEncode (x2)
    - sampling: KSampler
    - decoding: VAEDecode
    - output: PreviewImage (x2), VHS_VideoCombine
    - other operations: CreateVideo, GetVideoComponents, ImageBatch (x4), ImageToMask, MaskToImage (x2), ModelSamplingSD3, PrimitiveInt (x4), RepeatImageBatch, SolidMask (x2), TrimVideoLatent, WanVaceToVideo
- paired/multiple required: ImageBatch x4, CLIPTextEncode x2, LoadImage x2, MaskToImage x2, PreviewImage x2, SolidMask x2


# Image Edit  (`image_edit`)  -  3 workflow(s), 3 model(s)

## Image Edit / Flux 2 Klein  (`image_edit__flux_2_klein`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to edit an existing image using Flux 2 Klein.
- example request: "build an image workflow using Flux 2 Klein"
- description: [Local] image editing via Flux. 1 image input -> 1 image output. Performs image editing using the Flux 2 Klein distilled model.
- member workflows:
    - image_flux2_klein_image_edit_9b_distilled
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: CLIPLoader, UNETLoader, VAELoader
    - conditioning: CFGGuider, CLIPTextEncode, ConditioningZeroOut
    - latent / canvas: VAEEncode
    - sampling: KSamplerSelect, SamplerCustomAdvanced
    - decoding: VAEDecode
    - output: SaveImage
    - other operations: EmptyFlux2LatentImage, Flux2Scheduler, GetImageSize, ImageScaleToTotalPixels, RandomNoise, ReferenceLatent (x2)
- paired/multiple required: ReferenceLatent x2

## Image Edit / Qwen Image  (`image_edit__qwen_image`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate an image guided by a control map (canny/depth/pose) using Qwen Image.
- example request: "build an image workflow using Qwen Image"
- description: Local image editing via QWEN-Image-Edit-2511-Lightning. Up to 3 images (including optional depth/canny control inputs) -> 1 edited image output. Supports text-guided edits with optional structural control.
- member workflows:
    - qwen2511_imageEdit
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - model loading: CLIPLoader, LoraLoader, UNETLoader, VAELoader
    - conditioning: TextEncodeQwenImageEditPlus (x2)
    - latent / canvas: EmptyLatentImage
    - sampling: KSampler
    - decoding: VAEDecode
    - output: SaveImage
    - other operations: CFGNorm (x2), Image Load, ModelSamplingAuraFlow (x2)
- paired/multiple required: CFGNorm x2, LoadImage x2, ModelSamplingAuraFlow x2, TextEncodeQwenImageEditPlus x2

## Image Edit / Z-Image  (`image_edit__z_image`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to edit an existing image using Z-Image.
- example request: "build an image workflow using Z-Image"
- description: [Local] image-to-image via Z-Image-Turbo. 1 image input + text prompt -> 1 image output. Uses TextEncodeZImageOmni to feed the input image directly into conditioning for high-fidelity i2i edits. Denoise defaults to 0.75 - lower for more structure preservation, higher for more creative freedom.
- member workflows:
    - image_z_image_turbo_i2i
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: CLIPLoader, UNETLoader, VAELoader
    - conditioning: CLIPTextEncode, ConditioningZeroOut, TextEncodeZImageOmni
    - latent / canvas: EmptySD3LatentImage, VAEEncode
    - sampling: KSampler
    - decoding: VAEDecode
    - output: SaveImage
    - other operations: GetImageSize, ModelSamplingAuraFlow


# Text to Image  (`text_to_image`)  -  3 workflow(s), 3 model(s)

## Text to Image / Flux 2 Klein  (`text_to_image__flux_2_klein`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate an image from a text prompt using Flux 2 Klein.
- example request: "build an image workflow using Flux 2 Klein"
- description: Generate an image from a text prompt using Flux 2 Klein. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: STRING; outputs: IMAGE.
- member workflows:
    - image_flux2_klein_text_to_image
- node clusters (required structure):
    - model loading: CLIPLoader, UNETLoader, VAELoader
    - conditioning: CFGGuider, CLIPTextEncode (x2)
    - sampling: KSamplerSelect, SamplerCustomAdvanced
    - decoding: VAEDecode
    - output: SaveImage
    - other operations: EmptyFlux2LatentImage, Flux2Scheduler, PrimitiveInt (x2), PrimitiveStringMultiline, RandomNoise
- paired/multiple required: CLIPTextEncode x2

## Text to Image / Generic  (`text_to_image__generic`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate an image.
- example request: "build an image workflow"
- description: [Local] OCIO color convert. 1 EXR (or PNG) in -> 1 PNG out. Loads via bepic_imageLoad (OIIO), applies bepic_colorTransform input ACES - ACEScg to output Output - sRGB with clamp on, saves 16-bit PNG via bEpic_imageSave (OIIO). For batches of non-contiguous frames, run one job per file and patch image_path + first_frame; keep auto_version false so saves go straight into the target folder.
- member workflows:
    - acescg_to_srgb
- node clusters (required structure):
    - other operations: bEpic_imageSave, bepic_colorTransform, bepic_imageLoad

## Text to Image / Z-Image  (`text_to_image__z_image`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate an image from a text prompt using Z-Image.
- example request: "build an image workflow using Z-Image"
- description: [Local] text-to-image via Z-Image-Turbo. 1 text input -> 1 image output. High-speed image generation from text prompts.
- member workflows:
    - image_z_image_turbo
- node clusters (required structure):
    - model loading: CLIPLoader, UNETLoader, VAELoader
    - conditioning: CLIPTextEncode, ConditioningZeroOut
    - latent / canvas: EmptySD3LatentImage
    - sampling: KSampler
    - decoding: VAEDecode
    - output: SaveImage
    - other operations: ModelSamplingAuraFlow


# API / Partner Nodes - Character  (`api_partner_nodes_character`)  -  2 workflow(s), 1 model(s)

## API / Partner Nodes - Character / Nano-Banana  (`api_partner_nodes_character__nano_banana`)  -  2 workflow(s)  -  source: custom
- execution: api (API nodes: GeminiImage2Node, GeminiNode)
- when to use: Use to generate a multi-pose character sheet using Nano-Banana.
- example request: "build an image workflow using Nano-Banana"
- description: API character sheet generation FOR FACE CLOSEUPS via Nano-Banana Pro. 1 character image -> 1 image output (3x3 sheet). Uses an LLM call to generate a prompt from the reference, then renders 9 character views with varying facial expressions in a single sheet. | API character sheet generation via Nano-Banana Pro. 1 character image -> 1 image output (3x3 sheet). Uses an LLM call to generate a prompt from the reference, then renders 9 character views with varying body pose in a single sheet.
- member workflows:
    - NanoBananaPro_3x3CharacterSheet
    - NanoBananaPro_3x3CharacterSheet_closeups
- node clusters (required structure):
    - inputs: LoadImage
    - output: SaveImage
    - other operations: GeminiImage2Node, GeminiNode, PrimitiveStringMultiline


# API / Partner Nodes - First / Last Frame to Video  (`api_partner_nodes_first_last_frame_to_video`)  -  2 workflow(s), 2 model(s)

## API / Partner Nodes - First / Last Frame to Video / Generic  (`api_partner_nodes_first_last_frame_to_video__generic`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: ByteDance2FirstLastFrameNode)
- when to use: Use to generate a video interpolating between a first and last frame.
- example request: "build a video workflow"
- description: API first-last-frame-to-video via Seedance 2.0 (ByteDance). 1 first frame image + 1 optional last frame image -> 1 video output. Generates video interpolated between keyframes with precise motion control.
- member workflows:
    - api_seedance2_i2v_flf
- node clusters (required structure):
    - inputs: LoadImage (x2)
    - output: VHS_VideoCombine
    - other operations: ByteDance2FirstLastFrameNode, GetVideoComponents
- paired/multiple required: LoadImage x2

## API / Partner Nodes - First / Last Frame to Video / Kling  (`api_partner_nodes_first_last_frame_to_video__kling`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: KlingOmniProFirstLastFrameNode)
- when to use: Use to generate a video interpolating between a first and last frame using Kling.
- example request: "build a video workflow using Kling"
- description: API first-last-frame-to-video via Kling O3 (Kling 3.0). Up to 4 reference/keyframe images -> 1 video output. Generates videos with precise semantic control, longer duration, and improved narrative coherence.
- member workflows:
    - api_kling_o3_flf2v
- node clusters (required structure):
    - inputs: LoadImage (x3)
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, ImageBatchMulti, KlingOmniProFirstLastFrameNode
- paired/multiple required: LoadImage x3


# API / Partner Nodes - Video to Video  (`api_partner_nodes_video_to_video`)  -  2 workflow(s), 2 model(s)

## API / Partner Nodes - Video to Video / Generic  (`api_partner_nodes_video_to_video__generic`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: ByteDance2ReferenceNode)
- when to use: Use to edit an existing video.
- example request: "build a video workflow"
- description: API reference-to-video via Seedance 2.0 (ByteDance). 1 reference image + 1 reference video -> 1 video output. Generates, edits, or extends video using multimodal references for subject consistency, video editing, and video extension.
- member workflows:
    - api_seedance2_reference2v
- node clusters (required structure):
    - inputs: LoadImage, LoadVideo
    - output: VHS_VideoCombine
    - other operations: ByteDance2ReferenceNode, GetVideoComponents

## API / Partner Nodes - Video to Video / Kling  (`api_partner_nodes_video_to_video__kling`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: KlingOmniProEditVideoNode)
- when to use: Use to edit an existing video using Kling.
- example request: "build a video workflow using Kling"
- description: API video editing via Kling O3. 1 video + 1 reference image -> 1 edited video output. Enables precise subject editing and scene composition with native audio-visual synchronization.
- member workflows:
    - api_kling_o3_video_edit
- node clusters (required structure):
    - inputs: LoadImage, LoadVideo
    - output: VHS_VideoCombine
    - other operations: GetVideoComponents, KlingOmniProEditVideoNode


# Image to Video  (`image_to_video`)  -  2 workflow(s), 2 model(s)

## Image to Video / LTX-2  (`image_to_video__ltx_2`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video from an input image using LTX-2.
- example request: "build a video workflow using LTX-2"
- description: Generate a video from an input image using LTX-2. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; starts from an empty latent; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: IMAGE, STRING; outputs: AUDIO, IMAGE, STRING.
- member workflows:
    - video_ltx2_3_i2v
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: CheckpointLoaderSimple, LTXVAudioVAELoader, LatentUpscaleModelLoader, LoraLoader, LoraLoaderModelOnly
    - conditioning: CFGGuider (x2), CLIPTextEncode (x2), LTXAVTextEncoderLoader, LTXVConditioning, ManualSigmas (x2)
    - latent / canvas: LTXVEmptyLatentAudio
    - sampling: KSamplerSelect (x2), LTXVLatentUpsampler, SamplerCustomAdvanced (x2)
    - decoding: LTXVAudioVAEDecode, VAEDecodeTiled
    - output: VHS_VideoCombine
    - other operations: ComfyMathExpression (x3), CreateVideo, EmptyLTXVLatentVideo, GetVideoComponents, LTXVConcatAVLatent (x2), LTXVCropGuides, LTXVImgToVideoInplace (x2), LTXVPreprocess, LTXVSeparateAVLatent (x2), PreviewAny, PrimitiveBoolean, PrimitiveInt (x4), PrimitiveStringMultiline, RandomNoise (x2), ResizeImageMaskNode, ResizeImagesByLongerEdge, TextGenerateLTX2Prompt
- paired/multiple required: CFGGuider x2, CLIPTextEncode x2, KSamplerSelect x2, LTXVConcatAVLatent x2, LTXVImgToVideoInplace x2, LTXVSeparateAVLatent x2, ManualSigmas x2, RandomNoise x2, SamplerCustomAdvanced x2

## Image to Video / WAN 2.2  (`image_to_video__wan_2_2`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate a video using WAN 2.2.
- example request: "build a video workflow using WAN 2.2"
- description: Generate a video using WAN 2.2. Structurally it loads a diffusion model; uses a VAE; encodes a text prompt; runs a diffusion sampler; decodes the latent to pixels. Boundary inputs: IMAGE; outputs: AUDIO, IMAGE.
- member workflows:
    - video_wan2_2_14B_fun_camera
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: CLIPLoader, UNETLoader (x2), VAELoader
    - conditioning: CLIPTextEncode (x2)
    - sampling: KSamplerAdvanced (x2)
    - decoding: VAEDecode
    - output: VHS_VideoCombine
    - other operations: CreateVideo, GetVideoComponents, ModelSamplingSD3 (x2), WanCameraEmbedding, WanCameraImageToVideo
- paired/multiple required: CLIPTextEncode x2, KSamplerAdvanced x2, ModelSamplingSD3 x2, UNETLoader x2


# Upscale  (`upscale`)  -  2 workflow(s), 2 model(s)

## Upscale / Flux  (`upscale__flux`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to upscale / enhance an image using Flux.
- example request: "build an image workflow using Flux"
- description: Local image upscaling using UltimateSD upscale node (this uses a diffusion model for the upscale process, allowing a creative upscale that invents details). Setup with Flux-1 dev fp8. 1 image -> 1 upscaled image output.
- member workflows:
    - upscale_ultimateSD
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: CheckpointLoaderSimple, UpscaleModelLoader
    - conditioning: CLIPTextEncode (x2)
    - output: SaveImage
    - other operations: UltimateSDUpscale
- paired/multiple required: CLIPTextEncode x2

## Upscale / Generic  (`upscale__generic`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to upscale / enhance an image.
- example request: "build an image workflow"
- description: Local, simple image upscaling via specified ESRGAN model. 1 image -> 1 upscaled image output. Supports various models.
- member workflows:
    - upscale_using_model
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: UpscaleModelLoader
    - output: SaveImage
    - other operations: ImageUpscaleWithModel


# API / Partner Nodes - Inpaint / Outpaint  (`api_partner_nodes_inpaint_outpaint`)  -  1 workflow(s), 1 model(s)

## API / Partner Nodes - Inpaint / Outpaint / Nano-Banana  (`api_partner_nodes_inpaint_outpaint__nano_banana`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: GeminiNanoBanana2)
- when to use: Use to outpaint / extend an image beyond its borders using Nano-Banana.
- example request: "build an image workflow using Nano-Banana"
- description: API upscale and outpaint via Nano-Banana 2. 1 image -> 1 image output. Upscales the input image while also generating new content around the edges to expand the overall dimensions, guided by the original image's style and content.
- member workflows:
    - NanoBanana2_outpaintUpscale
- node clusters (required structure):
    - inputs: LoadImage
    - output: SaveImage
    - other operations: GeminiNanoBanana2


# API / Partner Nodes - Text to Image  (`api_partner_nodes_text_to_image`)  -  1 workflow(s), 1 model(s)

## API / Partner Nodes - Text to Image / Ideogram  (`api_partner_nodes_text_to_image__ideogram`)  -  1 workflow(s)  -  source: custom
- execution: api (API nodes: IdeogramV3)
- when to use: Use to generate an image from a text prompt using Ideogram.
- example request: "build an image workflow using Ideogram"
- description: Generate an image from a text prompt using Ideogram. Structurally it applies a sequence of node operations. Boundary inputs: IMAGE; outputs: IMAGE.
- member workflows:
    - api_ideogram_v3_t2i
- node clusters (required structure):
    - output: SaveImage
    - other operations: IdeogramV3


# Image Edit with ControlNet  (`image_edit_with_controlnet`)  -  1 workflow(s), 1 model(s)

## Image Edit with ControlNet / Z-Image  (`image_edit_with_controlnet__z_image`)  -  1 workflow(s)  -  source: custom
- execution: local
- when to use: Use to generate an image guided by a control map (canny/depth/pose) using Z-Image.
- example request: "build an image workflow using Z-Image"
- description: [Local] image editing via Z-Image-Turbo. 1 image input -> 1 image output. Uses ControlNet for precise and controlled image editing.
- member workflows:
    - image_z_image_turbo_fun_union_controlnet
- node clusters (required structure):
    - inputs: LoadImage
    - model loading: CLIPLoader, ModelPatchLoader, UNETLoader, VAELoader
    - conditioning: CLIPTextEncode, ConditioningZeroOut, QwenImageDiffsynthControlnet
    - latent / canvas: EmptySD3LatentImage
    - sampling: KSampler
    - decoding: VAEDecode
    - output: SaveImage
    - other operations: Canny, GetImageSize, ModelSamplingAuraFlow


# Text Tools  (`text_tools`)  -  1 workflow(s), 1 model(s)

## Text Tools / Gemini  (`text_tools__gemini`)  -  1 workflow(s)  -  source: custom
- execution: hybrid (API nodes: GeminiNode)
- when to use: Use to describe the motion in a video as text using Gemini.
- example request: "build a text workflow using Gemini"
- description: [API] motion prompt generation via Gemini, analyses a video and output a desscription of the motion in it. 1 video input -> 1 output. Generates descriptive motion prompts for video generation.
- member workflows:
    - video_gemini_motionPromptGeneration
- node clusters (required structure):
    - inputs: LoadVideo
    - other operations: CreateVideo, GeminiNode, GetVideoComponents, ImageResizeKJv2, easy saveText

