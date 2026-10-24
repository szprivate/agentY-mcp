# Claude Code plugin audit (2026-10-24, against Claude Code 2.1.309 docs)

Checked: `.claude-plugin/`, `agents/`, `commands/`, `skills/`, `manifest.json` (.mcpb), the server
definition. Fixed in the same change unless marked OPEN.

## Findings

| # | Finding | State |
|---|---|---|
| 1 | `marketplace.json` pointed at `./dist/agentY-plugin/agenty`, a build output that is not in git. Adding the repo as a marketplace installed nothing. | Fixed: the plugin is the repo root (`"source": "./"`). |
| 2 | No `.claude-plugin/plugin.json` and no `.mcp.json` in the repo (both only existed inside the ignored `dist/` build). | Fixed: both committed. `claude plugin validate .` passes (only an "icon missing" directory warning). |
| 3 | Versions stuck: `manifest.json` 1.0.0, `build_plugin.ps1` wrote 1.1.0, releases are v1.4.0. | Fixed: `scripts/update_manifest.py` sets plugin.json, the marketplace entry and manifest.json to the release version; agentY's `make_release.py` runs it. A test fails when the three differ. |
| 4 | Server definition relied on a vendored `runtime/python.exe` + `lib/` that exists only after the build scripts run. | Fixed: `.mcp.json` runs `uv run --no-project --with-requirements ${CLAUDE_PLUGIN_ROOT}/requirements-plugin.txt python -m src` with `PYTHONPATH=${CLAUDE_PLUGIN_ROOT}` (Claude Code ignores `cwd` for plugin servers). uv keeps the environment in its own cache, so it works from a plugin cache with no `.venv`, survives updates, and never touches the installer's `.venv`. |
| 5 | `skills/` was an old diverged copy: 19 skills (comfyui-generate, comfyui-core, batch-process, ... all removed from agentY) vs 32 in agentY. `skills_story/` duplicated story skills that are now ordinary agentY skills. | Fixed: `skills/` is a mirror made by agentY's `scripts/sync_plugin_skills.py` (26 shipped, 6 host-only excluded with reasons in `agentY/config/plugin_skills.json`). `skills_story/` deleted. |
| 6 | `agents/` and `commands/` named skills that no longer exist (`comfyui-generate`, `comfyui-core`, `batch-handoff`, `troubleshooting`, `feedback-loop`, `cinematography`, `reference-scout`). Tool names in them were all still valid. | Fixed: references replaced by current skills/tools (`workflow-templates`, `output-paths`, `run_variants`, `get_logs`, `memory_read`). Tests check every tool and skill name the agents/commands mention. |
| 7 | `manifest.json` (.mcpb) listed ~49 tools; the server offers 111. | Fixed: `update_manifest.py` regenerates `tools`; a test fails when it is stale. |
| 8 | Agents/commands described the removed Triage/Planner/Brain chain. | Fixed: all eight agents and both old commands deleted. Kept: `agenty` (sonnet) and `agenty-scout` (haiku, read-only), and commands `/agenty-generate`, `/agenty-model-from-photo`, `/agenty-destroy`, `/agenty-atlas`, `/agenty-cost`, which point at skills and tools. A test checks every tool and skill they name exists. |
| 9 | Skills reach non-Claude-Code clients nowhere. | Fixed: `list_skills`, `read_skill`, and each skill as an MCP prompt; server instructions say to check them first. |
| 10 | A marketplace added from GitHub is copied into the plugin cache: no `.venv`, no sibling agentY-core. | Fixed: uv builds the env (see 4); `src/__init__.py` clones agentY-core at the tag in `core.pin` (the release script bumps it) into `$CLAUDE_PLUGIN_DATA`, which also supplies the template corpus (`pip install` of core would not). Tested for real: `claude plugin marketplace add <github url>#dev`, `install`, `claude mcp list` shows Connected with all 111 tools, in an isolated Claude config. Keys: `AGENTY_ENV_FILE` / `AGENTY_HOME` / sibling agentY, else `$CLAUDE_PLUGIN_DATA/.env` or `~/.agenty/.env`. |
| 11 | `build_plugin.ps1` / `build_mcpb.ps1` (vendored-runtime builds) still exist; the first now duplicates the repo-root plugin. | OPEN: kept for the Claude Desktop .mcpb; `skills_story` removed from both. |

## Install / update (user steps)

From GitHub (first start slow, once - see the README):

    claude plugin marketplace add szprivate/agentY-mcp
    claude plugin install agenty@agentY
    claude plugin marketplace update agentY ; claude plugin update agenty@agentY     # later

From the local checkout (the installer's optional step does this); a `git pull` is the update:

    claude plugin marketplace add <path to agentY-mcp>
    claude plugin install agenty@agentY

Skills inside the plugin change only through a release or a manual
`agentY/scripts/sync_plugin_skills.py` + commit.
