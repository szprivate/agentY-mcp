**agentY** is a ComfyUI AI agent powered by a multi-stage pipeline:

- **Triage** - classifies your request and routes it to the right handler
- **Planner** - breaks complex multi-step requests into an ordered execution plan
- **Researcher** - resolves each step into a structured workflow specification
- **Brain** - assembles, executes, and quality-checks the ComfyUI workflow
- **QA Checker** - validates output before returning results

---

## What you can do

- **Generate images** - "Generate a cinematic wide-shot of Tokyo neon streets at night"
- **Edit images** - attach a photo and describe the change you want
- **Style transfer** - "Apply a Studio Ghibli style to my image"
- **Batch generation** - "Create 5 variations of this portrait in different lighting"
- **Planned batched workflows** - "Create an image, upscale it, then animate it with Kling 3.0"
- **Video generation** - "Animate this image as a slow zoom-in"
- **Image-to-video** - attach an image and request motion: "Make this pan slowly to the right"
- **Upscaling** - "Upscale this image with Topaz" or "Creative upscale with Magnific"

## Attaching images

Click the attachment button to upload images directly into the chat.
agentY will automatically detect them and wire them into the correct ComfyUI nodes.

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

## Tips

- Be descriptive - more detail produces better results
- Mention aspect ratio, lighting mood, or style references when relevant
- Follow up naturally: "Make it warmer", "Try a higher contrast version". It helps to add "Feedback:" in your answer, to make sure the Triage agent fully understand your intent is a follow-up.
- For multi-step jobs, describe the full pipeline: "Generate, upscale, then animate"

---

*Configuration is read from `config/settings.json` and `.env` in the project root.*
