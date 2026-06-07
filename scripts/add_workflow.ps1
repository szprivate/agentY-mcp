param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$WorkflowFile,
    [Parameter(Mandatory=$false, Position=1)]
    [string]$IndexPath = ""
)

# Resolve repo root (this script lives in <repo>/scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

if (-not (Test-Path $WorkflowFile)) {
    Write-Error "Workflow file not found: $WorkflowFile"
    exit 2
}

# ── Step 1: parse workflow and register in index ──────────────────────────────
$pyArgs = @('-m', 'src.utils.workflow_parser', $WorkflowFile)
if ($IndexPath -ne "") {
    $pyArgs += '--index-path'
    $pyArgs += $IndexPath
}

Write-Host "Running: python $($pyArgs -join ' ')"
& python @pyArgs
$exit = $LASTEXITCODE
if ($exit -ne 0) {
    Write-Error "add_workflow.ps1: parser exited with code $exit"
    exit $exit
}

# ── Step 2: update config/workflow_templates.json ────────────────────────────
$stem = [System.IO.Path]::GetFileNameWithoutExtension($WorkflowFile)
$templatesJson = Join-Path $RepoRoot "config\workflow_templates.json"
if (Test-Path $templatesJson) {
    $obj = Get-Content -Raw $templatesJson | ConvertFrom-Json
} else {
    $obj = [PSCustomObject]@{}
}
if (-not ($obj.PSObject.Properties.Name -contains $stem)) {
    $obj | Add-Member -NotePropertyName $stem -NotePropertyValue ""
    $json = ($obj | ConvertTo-Json -Depth 5) + "`n"
    [System.IO.File]::WriteAllText($templatesJson, $json, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "Added '$stem' to config/workflow_templates.json"
} else {
    Write-Host "Entry '$stem' already exists in config/workflow_templates.json"
}

exit 0
