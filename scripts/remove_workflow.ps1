param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Name,
    [Parameter(Mandatory=$false, Position=1)]
    [string]$IndexPath = ""
)

# Resolve repo root (this script lives in <repo>/scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

if (-not $Name) {
    Write-Error "Template name is required"
    exit 2
}

# ── Step 1: remove workflow from index ───────────────────────────────────────
$tmp = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Path]::GetRandomFileName() + '.py')
$py = @"
import sys
from pathlib import Path
sys.path.insert(0, r"$RepoRoot")
from src.utils.workflow_parser import workflow_remove
name = sys.argv[1]
index_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
result = workflow_remove(name, index_path=index_path)
print(result)
"@

$py | Out-File -FilePath $tmp -Encoding utf8

$pyArgs = @($tmp, $Name)
if ($IndexPath -ne "") { $pyArgs += $IndexPath }

Write-Host "Running: python $($pyArgs -join ' ')"
& python @pyArgs
$exit = $LASTEXITCODE
Remove-Item -Force -ErrorAction SilentlyContinue $tmp
if ($exit -ne 0) {
    Write-Error "remove_workflow.ps1: python exited with code $exit"
    exit $exit
}

# ── Step 2: update config/workflow_templates.json ────────────────────────────
$templatesJson = Join-Path $RepoRoot "config\workflow_templates.json"
if (Test-Path $templatesJson) {
    $obj = Get-Content -Raw $templatesJson | ConvertFrom-Json
    if ($obj.PSObject.Properties.Name -contains $Name) {
        $obj.PSObject.Properties.Remove($Name)
        $json = ($obj | ConvertTo-Json -Depth 5) + "`n"
        [System.IO.File]::WriteAllText($templatesJson, $json, (New-Object System.Text.UTF8Encoding $false))
        Write-Host "Removed '$Name' from config/workflow_templates.json"
    } else {
        Write-Host "Entry '$Name' not found in config/workflow_templates.json"
    }
}

# ── Step 3: remove skill directory ───────────────────────────────────────────
# Skill dirs use kebab-case derived from the template name
$kebab    = $Name.ToLower() -replace '_', '-'
$skillDir = Join-Path $RepoRoot "skills\$kebab"
if (Test-Path $skillDir) {
    Remove-Item -Recurse -Force $skillDir
    Write-Host "Removed skill directory: $skillDir"
} else {
    Write-Host "No skill directory found at '$skillDir' — nothing to remove."
}

exit 0
