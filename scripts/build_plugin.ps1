# Build the agentY Claude PLUGIN -- a single package that registers BOTH the MCP
# tools AND all agentY skills in one install.
#
# Unlike an .mcpb (which carries tools only -- the bundle manifest has no skills
# field), a Claude plugin bundles "MCP connectors, skills, slash commands, hooks"
# in one directory. Claude Desktop and Claude Code both load:
#   .claude-plugin/plugin.json   plugin manifest
#   .mcp.json                    MCP server config (launches the vendored runtime)
#   skills/<name>/SKILL.md       auto-registered skills
#
# Output layout (dist/agentY-plugin is BOTH a one-plugin marketplace and host):
#   dist/agentY-plugin/
#     .claude-plugin/marketplace.json     <- lets `/plugin marketplace add` find it
#     agenty/                             <- the plugin (CLAUDE_PLUGIN_ROOT)
#       .claude-plugin/plugin.json
#       .mcp.json
#       runtime/  lib/                    <- vendored interpreter + deps (reused from the .mcpb build)
#       src/  config/  comfyui_workflow_templates_custom/
#       skills/<name>/                    <- every skill (skills + skills_story), folder == frontmatter name
#       README.md
#
# Prereq: run build_mcpb.ps1 first so dist/agentY/{runtime,lib} exist (this script
# reuses them instead of re-vendoring).

$ErrorActionPreference = "Stop"
$root      = Split-Path -Parent $PSScriptRoot
$mcpbStage = Join-Path $root "dist\agentY"
$mkt       = Join-Path $root "dist\agentY-plugin"
$plugin    = Join-Path $mkt  "agenty"
Set-Location $root

$srcRuntime = Join-Path $mcpbStage "runtime"
$srcLib     = Join-Path $mcpbStage "lib"
if (-not (Test-Path $srcRuntime) -or -not (Test-Path $srcLib)) {
    throw "Missing $srcRuntime or $srcLib. Run scripts\build_mcpb.ps1 first -- this script reuses the vendored runtime + lib."
}

Write-Host "[1/6] Resetting $mkt ..."
if (Test-Path $mkt) { Remove-Item -Recurse -Force $mkt }
New-Item -ItemType Directory -Force -Path (Join-Path $plugin ".claude-plugin") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $mkt ".claude-plugin") | Out-Null

Write-Host "[2/6] Copying server payload (src, config, templates)..."
Copy-Item -Recurse (Join-Path $root "src")    (Join-Path $plugin "src")
Copy-Item -Recurse (Join-Path $root "config") (Join-Path $plugin "config")
Copy-Item -Recurse (Join-Path $root "comfyui_workflow_templates_custom") (Join-Path $plugin "comfyui_workflow_templates_custom")

Write-Host "[3/6] Reusing vendored runtime/ + lib/ from the .mcpb build..."
robocopy $srcRuntime (Join-Path $plugin "runtime") /E /NFL /NDL /NJH /NJS /NP /NS /NC | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy runtime failed ($LASTEXITCODE)" }
robocopy $srcLib (Join-Path $plugin "lib") /E /NFL /NDL /NJH /NJS /NP /NS /NC | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy lib failed ($LASTEXITCODE)" }
$global:LASTEXITCODE = 0

Write-Host "[4/6] Normalizing skills (folder == frontmatter name; merge skills_story)..."
function Get-SkillName($skillMd) {
    foreach ($line in (Get-Content -LiteralPath $skillMd -TotalCount 15)) {
        if ($line -match '^\s*name:\s*(.+?)\s*$') { return $Matches[1] }
    }
    return $null
}
$skillsDest = Join-Path $plugin "skills"
New-Item -ItemType Directory -Force -Path $skillsDest | Out-Null
$skillCount = 0
foreach ($srcDir in @((Join-Path $root "skills"), (Join-Path $root "skills_story"))) {
    if (-not (Test-Path $srcDir)) { continue }
    foreach ($d in (Get-ChildItem -Directory -LiteralPath $srcDir)) {
        $md = Join-Path $d.FullName "SKILL.md"
        if (-not (Test-Path $md)) { continue }
        $name = Get-SkillName $md
        if (-not $name) { $name = $d.Name.ToLower() }
        $dest = Join-Path $skillsDest $name
        robocopy $d.FullName $dest /E /NFL /NDL /NJH /NJS /NP /NS /NC | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy skill '$name' failed ($LASTEXITCODE)" }
        $skillCount++
    }
}
$global:LASTEXITCODE = 0
Write-Host "    staged $skillCount skill(s)."

Write-Host "[5/6] Writing plugin.json, .mcp.json, marketplace.json, README..."
# Windows PowerShell's Set-Content -Encoding utf8 emits a BOM, which JSON / plugin
# loaders reject. Write UTF-8 *without* BOM.
function Write-Utf8NoBom($path, $content) {
    [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))
}
$pluginJson = @'
{
  "name": "agenty",
  "version": "1.0.0",
  "description": "agentY - turn natural language into ComfyUI image/video workflows. Bundles the agentY MCP server (49 tools) and all agentY skills.",
  "author": { "name": "szprivate", "url": "https://github.com/szprivate/agentY" },
  "homepage": "https://github.com/szprivate/agentY",
  "license": "MIT",
  "keywords": ["comfyui", "image-generation", "video-generation", "flux", "stable-diffusion"]
}
'@
Write-Utf8NoBom (Join-Path $plugin ".claude-plugin\plugin.json") $pluginJson

# .mcp.json -- single-quoted here-string so ${CLAUDE_PLUGIN_ROOT} stays literal.
$mcpJson = @'
{
  "mcpServers": {
    "agentY": {
      "command": "${CLAUDE_PLUGIN_ROOT}/runtime/python.exe",
      "args": ["-m", "src"],
      "cwd": "${CLAUDE_PLUGIN_ROOT}",
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}/lib;${CLAUDE_PLUGIN_ROOT}"
      }
    }
  }
}
'@
Write-Utf8NoBom (Join-Path $plugin ".mcp.json") $mcpJson

$marketplaceJson = @'
{
  "name": "agentY",
  "description": "agentY plugin marketplace (single self-contained plugin: agenty).",
  "owner": { "name": "szprivate", "url": "https://github.com/szprivate/agentY" },
  "plugins": [
    {
      "name": "agenty",
      "source": "./agenty",
      "description": "agentY MCP server (49 ComfyUI tools) + all agentY skills, self-contained with a vendored Python runtime.",
      "category": "media"
    }
  ]
}
'@
Write-Utf8NoBom (Join-Path $mkt ".claude-plugin\marketplace.json") $marketplaceJson

$readme = @'
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
'@
Write-Utf8NoBom (Join-Path $plugin "README.md") $readme

Write-Host "[6/6] Cleaning caches + self-test..."
Get-ChildItem -Recurse -Force -Path $plugin -Filter __pycache__ -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Force -Path $plugin -File -Filter *.pyc -ErrorAction SilentlyContinue | Remove-Item -Force

# Self-test: launch as the plugin would, with CLAUDE_PLUGIN_ROOT = the plugin dir.
$probeCode = "import sys; r=r'$plugin'; sys.path[:0]=[r+r'\lib', r]; import src.mcp_server as m; print('SELFTEST_TOOLS=%d' % len(m._TOOLS))"
$probe = & (Join-Path $plugin "runtime\python.exe") -c $probeCode
if ($LASTEXITCODE -ne 0 -or ($probe -notmatch "SELFTEST_TOOLS=\d+")) {
    Write-Host "Self-test output: $probe"
    throw "Plugin self-test FAILED -- the vendored interpreter could not import the server."
}
$skillDirs = (Get-ChildItem -Directory -LiteralPath $skillsDest).Count
Write-Host "[*] Self-test OK: $probe ; skills staged: $skillDirs"
$sizeMb = [Math]::Round(((Get-ChildItem -Recurse -Force $mkt | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host "Done. Plugin marketplace at $mkt ($sizeMb MB)."
