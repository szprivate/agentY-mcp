## What you can do

- **Generate images** - "Generate a cinematic wide-shot of Tokyo neon streets at night"
- **Edit images** - attach a photo and describe the change you want
- **Style transfer** - "Apply a Studio Ghibli style to my image"
- **Batch generation** - "Create 5 variations of this portrait in different lighting"
- **Planned batched workflows** - "Create an image, upscale it, then animate it with Kling 3.0"
- **Video generation** - "Animate this image as a slow zoom-in"
- **Image-to-video** - attach an image and request motion: "Make this pan slowly to the right"
- **Upscaling** - "Upscale this image with Topaz" or "Creative upscale with Magnific"
- **Prompt generation** - "Describe this image as a prompt for a video model", "Describe the motion in this video"

## Attaching images

Click the attachment button to upload images directly into the chat.
agentY will automatically detect them and wire them into the correct ComfyUI nodes.

## Tips

- Be descriptive - more detail produces better results
- Mention aspect ratio, lighting mood, or style references when relevant
- If you want a specific workflow / template: let the agent know! (eg "Use NanoBanana2 for this.")
- If you want to use a local workflow: let the agent know! (eg "Prefer to use a local workflow for this request")
- Follow up naturally: "Make it warmer", "Try a higher contrast version". It helps to add "Feedback:" to your request, to make sure the Triage agent fully understands your intent is a follow-up.
- For multi-step jobs, describe the full pipeline: "Generate, upscale, then animate", or "First, scale this image up, then make it 16:9, then animate it using Kling 3.0"


## Slash commands

Type `/` in the chat input to see available commands:

| Command | Description |
|---|---|
| `/restart` | Restart the agent pipeline |
| `/stop` | Stop and shut down the agent |
| `/unload` | Unload Ollama models from VRAM |
| `/clear_vram` | Clear ComfyUI GPU VRAM |
| `/clearhistory` | Delete all conversation history |
| `/switch_model <agent> <provider,model>` | Switch the LLM used by a specific agent |
| `/add_workflow <path/to/workflow.json>` | Add a ComfyUI workflow template |
| `/remove_workflow <template_name>` | Remove a workflow template by name |
| `/resend` | Resend the first user message of the current thread |

Use the **up/down arrow keys** in the chat input to browse your message history (up to 200 messages, persisted across reloads).

---

*Configuration is read from `config/settings.json` and `.env` in the project root.*
