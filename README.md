# agentY

An **MCP server + Claude Skills** that turn natural language into [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
image and video workflows. You drive it from an MCP host — **Claude Desktop** — which
acts as the orchestrator: it loads the agentY Skills (the procedural know-how) and calls
the agentY MCP tools (template selection, workflow assembly, validation, execution,
HuggingFace model management, image handling, web search, memory).

> **Migrated from a multi-agent pipeline.** agentY was previously a Strands-SDK
> application with its own Researcher/Brain/Executor agents, per-stage LLM routing
> (Claude **and** Ollama), a Chainlit web GUI, and Postgres/MinIO persistence. That
> orchestration now collapses into the model itself: Claude is the single brain, the
> tools are an MCP server, and the system prompts became Skills. **Ollama, Chainlit,
> Postgres, and MinIO are gone.** See [What changed](#what-changed).

---

## Architecture

```
Claude Desktop  (the orchestrator / "brain")
   │  loads Skills  ── skills/ , skills_story/   (procedural knowledge)
   │  calls MCP tools
   ▼
agentY MCP server  (python -m src, FastMCP over stdio)  ──HTTP/WS──►  ComfyUI
```

- **MCP server** — `src/mcp_server.py` exposes ~43 tools (see `src/tools/`). The
  ComfyUI client, workflow parser, and executor are reused unchanged minus Ollama.
- **Skills** — `skills/` (ComfyUI) and `skills_story/` (creative writing). The entry
  point is **`comfyui-generate`**, which orchestrates the full flow.
- **Vision QA** — `execute_workflow` returns the generated image(s) (or sampled video
  frames) as image content, so Claude inspects results with its own vision.

---

## Requirements

- **Python 3.11+**
- A running **ComfyUI** instance (default `http://127.0.0.1:8188`)
- **Claude Desktop** (the MCP host)
- A **HuggingFace token** (`HF_TOKEN`) for downloading gated models
- *(optional)* a **ComfyUI API key** if your ComfyUI requires auth / uses API nodes

No Anthropic API key is needed here — Claude Desktop supplies the model. No Ollama,
Docker, Postgres, or MinIO.

---

## Install — Option A: the `.mcpb` bundle (one-click, recommended)

agentY ships as a self-contained **MCP Bundle** (`.mcpb`) — the server plus all its
Python dependencies vendored in — that Claude Desktop installs in one step.

1. **Build it** (or use a prebuilt `dist/agentY.mcpb`):

   ```powershell
   .\scripts\build_mcpb.ps1
   ```

   This stages the runtime files, vendors the dependencies into `lib/`, and packs
   `dist\agentY.mcpb`. Build it with the **same Python** Claude Desktop will run
   (binary wheels like Pillow/pywin32 are version- and platform-specific). The bundle
   is **Windows + Python 3.11+** only.

2. **Install it:** in Claude Desktop, **Settings → Extensions → Install Extension…**
   (or drag-and-drop) and pick `dist\agentY.mcpb`.

3. **Configure it:** in the extension's settings, set your **HuggingFace token**,
   optional **ComfyUI API key**, and **ComfyUI URL** (defaults to `http://127.0.0.1:8188`).

4. **Install the Skills** (see [step 5 below](#5-install-the-skills)) — the bundle
   provides the *tools*; the Skills (the procedural know-how) are uploaded separately.

> The bundle runs `python -m src` from the extracted package, so a `python` matching
> the build must be on PATH. If you'd rather manage the environment yourself, use
> Option B.

---

## Install — Option B: run the MCP server directly

### 1. Clone and create a virtual environment

```powershell
git clone https://github.com/szprivate/agentY.git
cd agentY
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure secrets

```powershell
copy .env_example .env
```

Edit `.env`:

```dotenv
HF_TOKEN=hf_...
COMFYUI_API_KEY=          # blank for an unauthenticated local ComfyUI
# MEMORY_ENABLED=false    # optional: disable the long-term memory tools
```

### 3. Configure defaults (optional)

Edit `config/settings.json` to point at your ComfyUI instance and model directory:

```jsonc
{
  "comfyui_url": "http://127.0.0.1:8188",
  "comfyui_models_dir": "L:\\software\\comfyui\\Models",
  "comfyui_custom_templates_dir": "./comfyui_workflow_templates_custom/templates/",
  "output_dir": "./output_images/",
  "output_workflows_dir": "./output_workflows/",
  "comfyui_user_dir": "D:\\ai\\ComfyUI\\user\\default"
}
```

### 4. Register the MCP server with Claude Desktop

Merge `claude_desktop_config.example.json` into your Claude Desktop config
(**Settings → Developer → Edit Config**, or
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "agentY": {
      "command": "D:\\AI\\agentY-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "src"],
      "cwd": "D:\\AI\\agentY-mcp",
      "env": { "HF_TOKEN": "hf_your_token_here", "COMFYUI_API_KEY": "" }
    }
  }
}
```

Use the **absolute** path to the venv's `python.exe`, and set `cwd` to the repo root.
Restart Claude Desktop — the **agentY** tools should appear.

### 5. Install the Skills

In Claude Desktop, **Settings → Capabilities → Skills → Upload skill**, then upload
each skill folder (zip the folder so `SKILL.md` is at the zip root). The key one is
**`comfyui-generate`**; the others (`comfyui-core`, `prompt-craft`, `workflow-templates`,
`assemble-from-template`, `assemble-new-workflow`, `cinematography`, `reference-scout`,
the `story-*` skills, etc.) are activated by `comfyui-generate` as needed.

---

## Usage

Open Claude Desktop with the agentY server connected and just ask, e.g.:

- *"Generate a cinematic wide shot of Tokyo at night."*
- *"Edit this photo to make it daytime."* (attach an image)
- *"Make 5 variations of a red sports car, different angles."*
- *"Upscale the last image with UltimateSD."*
- *"Write a 6-shot storyboard about a lighthouse keeper and render it as Kling clips."*

Claude selects a template, resolves/downloads models, assembles and validates the
workflow, runs it, then shows you the result and iterates on feedback.

### Verify the server independently

```bash
# List the tools the server exposes
npx @modelcontextprotocol/inspector python -m src
```

---

## Adding custom workflow templates

```powershell
# Register a workflow JSON (also generates a SKILL.md)
.\scripts\add_workflow.ps1 path\to\your_workflow_api.json

# Remove a registered template
.\scripts\remove_workflow.ps1 your_workflow_api
```

Custom templates live in `comfyui_workflow_templates_custom/templates/` and are indexed
in `config/workflow_templates.json`.

---

## What changed

| Capability | Status after migration |
|---|---|
| NL → ComfyUI workflow, image/video generation & editing | ✅ Preserved (MCP tools + skills) |
| Template select / assemble / patch / validate / batch / variations | ✅ Preserved |
| Workflow execution + progress + output collection | ✅ Preserved (`execute_workflow`) |
| HuggingFace model search/download | ✅ Preserved |
| Web search + reference scouting | ✅ Preserved (`reference-scout`) |
| Multi-step planning | ✅ Preserved (Claude plans natively) |
| Story / synopsis / scene / storyboard / cinematography (DoP) | ✅ Preserved (skills) |
| Long-term memory tools | ✅ Preserved — local file store (keyword search; no vector recall) |
| Vision QA of outputs | ⚠️ Now Claude's native vision (no Ollama QA model) |
| Triage routing | ⚠️ Absorbed into Claude's reasoning |
| Chainlit GUI, Postgres threads, MinIO storage, cost tracking | ❌ Removed — Claude Desktop is the UI |
| ComfyUI → agentY Flask bridge | ❌ Removed |
| Ollama (all stages) | ❌ Removed |

---

## License

MIT
