# Build agentY.mcpb — a self-contained MCP bundle for Claude Desktop (Windows).
#
# Stages the runtime files, vendors every Python dependency into lib/, then packs
# with the official mcpb CLI. The bundle is self-contained: pywin32's loader dirs are
# registered at startup by src/__init__.py so the mcp SDK imports without the host's
# site-packages.
#
# Requirements:
#   - python on PATH, matching the interpreter Claude Desktop will launch (binary
#     wheels such as Pillow/pywin32 are version- and platform-specific).
#   - Node / npx (for @anthropic-ai/mcpb).
#
# NOTE: `pip install --target` SKIPS dependencies already present in the active
# environment, which would leave the bundle incomplete — `--ignore-installed` forces
# every (transitive) dependency into lib/.

$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root "dist\agentY"
$out   = Join-Path $root "dist\agentY.mcpb"
Set-Location $root

Write-Host "[1/4] Staging files..."
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item manifest.json, requirements.txt $stage
Copy-Item -Recurse src, config, skills, skills_story, comfyui_workflow_templates_custom $stage

Write-Host "[2/4] Vendoring dependencies into lib/ (downloads wheels)..."
python -m pip install --target "$stage\lib" --ignore-installed -r requirements.txt --quiet --disable-pip-version-check

Write-Host "[3/4] Cleaning caches..."
Get-ChildItem -Recurse -Force -Path $stage -Filter __pycache__ -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Force -Path $stage -File -Filter *.pyc -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "[4/4] Packing..."
npx -y "@anthropic-ai/mcpb@latest" pack $stage $out

Write-Host "Done -> $out"
