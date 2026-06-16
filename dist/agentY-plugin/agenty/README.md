# agentY (Claude plugin)

Self-contained plugin: the agentY MCP server (49 ComfyUI tools) plus every agentY
skill, with a vendored Python runtime -- no system Python needed.

## Install (Claude Code)
    /plugin marketplace add <path-to>/dist/agentY-plugin
    /plugin install agenty@agentY

## Install (Claude Desktop)
Settings -> Plugins -> add this folder / its git repo, then enable "agenty".

The MCP server launches via .mcp.json using ${CLAUDE_PLUGIN_ROOT}/runtime/python.exe.
Skills under skills/ register automatically.
