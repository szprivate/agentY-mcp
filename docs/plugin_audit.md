# Claude Code plugin audit (2026-10-24, against Claude Code 2.1.309 docs)

Checked: `.claude-plugin/`, `agents/`, `commands/`, `skills/`, `manifest.json` (.mcpb), the server
definition. Fixed in the same change unless marked OPEN.

## Findings

| # | Finding | State |
|---|---|---|
| 1 | `marketplace.json` pointed at `./dist/agentY-plugin/agenty`, a build output that is not in git. Adding the repo as a marketplace installed nothing. | Fixed: the plugin is the repo root (`"source": "./"`). |
| 2 | No `.claude-plugin/plugin.json` and no `.mcp.json` in the repo (both only existed inside the ignored `dist/` build). | Fixed: both committed. `claude plugin validate .` passes (only an "icon missing" directory warning). |
| 3 | Versions stuck: `manifest.json` 1.0.0, `build_plugin.ps1` wrote 1.1.0, releases are v1.4.0. | Fixed: `scripts/update_manifest.py` sets plugin.json, the marketplace entry and manifest.json to the release version; agentY's `make_release.py` runs it. A test fails when the three differ. |
| 4 | Server definition relied on a vendored `runtime/python.exe` + `lib/` that exists only after `build_mcpb.ps1` + `build_plugin.ps1` (about 100s of MB). | Fixed: `.mcp.json` runs `uv run --no-project --python ${CLAUDE_PLUGIN_ROOT}/.venv python -m src` (works on Windows and macOS, no path to python.exe). Started and answered `initialize` in a test. |
| 5 | `skills/` was an old diverged copy: 19 skills (comfyui-generate, comfyui-core, batch-process, ... all removed from agentY) vs 32 in agentY. `skills_story/` duplicated story skills that are now ordinary agentY skills. | Fixed: `skills/` is a mirror made by agentY's `scripts/sync_plugin_skills.py` (26 shipped, 6 host-only excluded with reasons in `agentY/config/plugin_skills.json`). `skills_story/` deleted. |
| 6 | `agents/` and `commands/` named skills that no longer exist (`comfyui-generate`, `comfyui-core`, `batch-handoff`, `troubleshooting`, `feedback-loop`, `cinematography`, `reference-scout`). Tool names in them were all still valid. | Fixed: references replaced by current skills/tools (`workflow-templates`, `output-paths`, `run_variants`, `get_logs`, `memory_read`). Tests check every tool and skill name the agents/commands mention. |
| 7 | `manifest.json` (.mcpb) listed ~49 tools; the server offers 111. | Fixed: `update_manifest.py` regenerates `tools`; a test fails when it is stale. |
| 8 | Agents/commands still describe the old Triage/Planner/Brain pipeline. They work, but do not cover newer tools (partner_run, dcc_build, atlas_*, ayon_*, deadline, estimate_workflow_cost, agenty_turn) except through the skills. | OPEN, by design: the skills carry the know-how, and with `list_skills` the model finds them. Rewriting the agents is a product decision. |
| 9 | Skills reach non-Claude-Code clients nowhere. | Fixed: `list_skills`, `read_skill`, and each skill as an MCP prompt; server instructions say to check them first. |
| 10 | A marketplace added from GitHub is copied into the plugin cache and has no `.venv`, so the server cannot start there. | OPEN, documented: install from the local checkout (`claude plugin marketplace add <path to agentY-mcp>`), which is what the installer does. Claude Code reads a local-path marketplace in place. |
| 11 | `build_plugin.ps1` / `build_mcpb.ps1` (vendored-runtime builds) still exist; the first now duplicates the repo-root plugin. | OPEN: kept for the Claude Desktop .mcpb; `skills_story` removed from both. |

## Install / update (user steps)

    claude plugin marketplace add D:\ai\agentY-mcp
    claude plugin install agenty@agentY

Update after a release: `git pull` in agentY-mcp (the installer / launcher does it), then
`claude plugin marketplace update agentY` and `claude plugin update agenty@agentY`, restart Claude Code.
Skills inside the plugin change only through a release or a manual
`agentY/scripts/sync_plugin_skills.py` + commit.
