# Build agentY.mcpb -- a SELF-CONTAINED MCP bundle for Claude Desktop (Windows).
#
# The bundle ships everything it needs so it installs with one drag-and-drop and
# runs regardless of what Python (if any) the user has:
#
#   runtime/   a standalone CPython 3.12 interpreter (copied from the build venv's
#              base interpreter -- a python-build-standalone / uv distribution).
#   lib/       every Python dependency, vendored via pip --target.
#   src, ...   the server, config, skills, and workflow templates.
#
# The manifest launches  ${__dirname}\runtime\python.exe -m src  with
# PYTHONPATH=${__dirname}\lib;${__dirname}, so no system Python is involved.
# pywin32's loader dirs are registered at startup by src/__init__.py.
#
# Requirements (build machine only):
#   - A repo .venv created from a standalone CPython 3.12 (uv venv / python-build-
#     standalone). Its base interpreter is copied wholesale into runtime/.
#   - Node / npx (for @anthropic-ai/mcpb).
#
# NOTE: deps are vendored with the *copied runtime* interpreter so the wheels
# (Pillow, pywin32, numpy, ...) match the exact interpreter that ships in the
# bundle. --ignore-installed forces every transitive dependency into lib/.

$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root "dist\agentY"
$out   = Join-Path $root "dist\agentY.mcpb"
Set-Location $root

# -- Resolve the build interpreter + its standalone home ----------------------
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    throw "Build venv not found at $venvPy. Create it from a standalone CPython 3.12 (e.g. 'uv venv')."
}
$pyHome = (& $venvPy -c "import sys; print(sys.base_prefix)").Trim()
$srcRuntimePy = Join-Path $pyHome "python.exe"
if (-not (Test-Path $srcRuntimePy)) {
    throw "Standalone interpreter not found at $srcRuntimePy (base_prefix of the venv). The venv must be built from a relocatable standalone CPython."
}
$pyVer = (& $srcRuntimePy -c "import sys; print('%d.%d.%d' % sys.version_info[:3])").Trim()
Write-Host "[*] Build interpreter : $srcRuntimePy (CPython $pyVer)"

Write-Host "[1/6] Staging files..."
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item manifest.json, requirements.txt $stage
Copy-Item -Recurse src, config, skills, skills_story, comfyui_workflow_templates_custom $stage

Write-Host "[2/6] Vendoring the Python runtime into runtime/ ..."
$stageRuntime = Join-Path $stage "runtime"
# robocopy, not Copy-Item: Copy-Item -Recurse throws "already exists" on the many
# nested __pycache__ dirs in a CPython tree. robocopy exit codes < 8 are success.
robocopy $pyHome $stageRuntime /E /NFL /NDL /NJH /NJS /NP /NS /NC | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy of the runtime failed (exit $LASTEXITCODE)." }
$global:LASTEXITCODE = 0
$stageRuntimePy = Join-Path $stageRuntime "python.exe"

Write-Host "[3/6] Trimming the runtime (test suites, tcl/tk, idle, headers) ..."
$prune = @(
    (Join-Path $stageRuntime "Lib\test"),
    (Join-Path $stageRuntime "Lib\idlelib"),
    (Join-Path $stageRuntime "Lib\tkinter"),
    (Join-Path $stageRuntime "Lib\turtledemo"),
    (Join-Path $stageRuntime "tcl"),
    (Join-Path $stageRuntime "include"),
    (Join-Path $stageRuntime "libs")
)
foreach ($p in $prune) {
    if (Test-Path $p) { Remove-Item -Recurse -Force $p -ErrorAction SilentlyContinue }
}

Write-Host "[4/6] Vendoring dependencies into lib/ (downloads wheels)..."
& $stageRuntimePy -m pip install --target "$stage\lib" --ignore-installed -r requirements.txt --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw "pip install into lib/ failed (exit $LASTEXITCODE)." }

Write-Host "[5/6] Cleaning caches..."
Get-ChildItem -Recurse -Force -Path $stage -Filter __pycache__ -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Force -Path $stage -File -Filter *.pyc -ErrorAction SilentlyContinue | Remove-Item -Force

# Self-test the staged bundle BEFORE packing: launch the vendored interpreter
# against the vendored libs and confirm the MCP server imports + registers.
Write-Host "[*] Self-test: launching the vendored interpreter against vendored libs..."
$probeCode = "import sys; sys.path[:0]=[r'$stage\lib', r'$stage']; import src.mcp_server as m; print('SELFTEST_TOOLS=%d' % len(m._TOOLS))"
$probe = & $stageRuntimePy -c $probeCode
if ($LASTEXITCODE -ne 0 -or ($probe -notmatch "SELFTEST_TOOLS=\d+")) {
    Write-Host "Self-test output: $probe"
    throw "Staged bundle self-test FAILED: the vendored interpreter could not import the server. See stderr above."
}
Write-Host "[*] Self-test OK: $probe"

Write-Host "[6/6] Packing..."
npx -y "@anthropic-ai/mcpb@latest" pack $stage $out

$sizeMb = [Math]::Round((Get-Item $out).Length / 1MB, 1)
Write-Host "Done. Wrote $out ($sizeMb MB, self-contained: runtime + lib + src)."
