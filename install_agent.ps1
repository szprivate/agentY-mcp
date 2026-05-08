<#
.SYNOPSIS
    Cross-platform install script for the agentY project.
    Works on Windows PowerShell 5.1+ and PowerShell 7+, and macOS with PowerShell 7+.
#>

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

# Detect Windows once, deterministically. $IsWindows is a PS 7 automatic variable;
# PS 5.1 only exists on Windows, so default to $true when the variable is missing.
$Script:OnWindows = $true
if (Get-Variable -Name IsWindows -Scope Global -ErrorAction SilentlyContinue) {
    $Script:OnWindows = [bool]$IsWindows
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "---  $Text  ---" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "  [ok] $Text" -ForegroundColor Green
}

function Write-Info {
    param([string]$Text)
    Write-Host "  [i]  $Text" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Text)
    Write-Host "  [!]  $Text" -ForegroundColor Red
}

function Exit-WithError {
    param([string]$Message, [int]$Code = 1)
    Write-Fail $Message
    exit $Code
}

# Test whether the Docker daemon is reachable without triggering NativeCommandError.
# PS 5.1 turns native-command stderr into a NativeCommandError object even when
# all streams are redirected to $null, because $ErrorActionPreference='Stop'
# intercepts it before the redirection takes effect. Wrapping in a try/catch
# with a local Continue preference is the reliable cross-version workaround.
function Test-DockerRunning {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        docker info *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $prev
    }
}

# Replace or append a KEY=VALUE line in a file.
function Set-EnvKey {
    param(
        [string]$FilePath,
        [string]$Key,
        [string]$Value
    )
    $content = Get-Content $FilePath -Raw
    if ($null -eq $content) { $content = "" }

    # Values containing characters that docker-compose's .env parser would
    # interpolate ($, #, leading/trailing whitespace) must be single-quoted
    # so both docker-compose and python-dotenv treat them as literal.
    $needsQuoting = ($Value -match '[\$#]') -or ($Value -ne $Value.Trim()) -or ($Value -eq "")
    if ($needsQuoting) {
        if ($Value -match "'") {
            Exit-WithError "Cannot write $Key to .env: value contains a single quote, which is not supported."
        }
        $writtenValue = "'$Value'"
    } else {
        $writtenValue = $Value
    }

    # Escape the key for regex use
    $escapedKey = [regex]::Escape($Key)
    $pattern    = "(?m)^$escapedKey=.*$"
    $replacement = "$Key=$writtenValue"

    if ($content -match $pattern) {
        $content = $content -replace $pattern, $replacement
    } else {
        # Ensure file ends with a newline before appending
        if ($content.Length -gt 0 -and -not $content.EndsWith("`n")) {
            $content += "`n"
        }
        $content += "$replacement`n"
    }

    # Write without BOM, unix line endings inside the file are fine
    [System.IO.File]::WriteAllText($FilePath, $content, [System.Text.UTF8Encoding]::new($false))
}

# ---------------------------------------------------------------------------
# Resolve script / project root
# ---------------------------------------------------------------------------
$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Location).Path
}

# ---------------------------------------------------------------------------
# 1. Preflight checks
# ---------------------------------------------------------------------------

Write-Header "1 / 9  Preflight checks"

# uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Exit-WithError @"
'uv' is not installed or not on PATH.
Install it from: https://docs.astral.sh/uv/getting-started/installation/
"@
}
Write-Success "uv found: $(uv --version)"

# git (needed to clone chainlit-datalayer)
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Exit-WithError "git is not installed or not on PATH. Install it from https://git-scm.com/ and try again."
}
Write-Success "git found: $(git --version)"

# Docker CLI
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Exit-WithError "Docker is not installed or not on PATH. Install Docker Desktop and try again."
}
Write-Success "Docker CLI found"

# Docker daemon running.
if (-not (Test-DockerRunning)) {
    Write-Info "Docker daemon is not running. Attempting to start it..."
    if ($Script:OnWindows) {
        # Try to launch Docker Desktop on Windows
        $dockerDesktopPaths = @(
            "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
            "$env:LOCALAPPDATA\Programs\Docker\Docker\Docker Desktop.exe"
        )
        $launched = $false
        foreach ($path in $dockerDesktopPaths) {
            if (Test-Path $path) {
                Start-Process $path
                $launched = $true
                Write-Info "Docker Desktop launched from: $path"
                break
            }
        }
        if (-not $launched) {
            Exit-WithError "Could not find Docker Desktop to launch. Start it manually and try again."
        }
    } else {
        # On Linux/macOS, try to start the Docker service
        $startResult = $null
        if (Get-Command systemctl -ErrorAction SilentlyContinue) {
            $startResult = & sudo systemctl start docker 2>&1
        } elseif (Get-Command service -ErrorAction SilentlyContinue) {
            $startResult = & sudo service docker start 2>&1
        } else {
            Exit-WithError "Cannot start Docker automatically on this system. Start the Docker daemon manually and try again."
        }
    }

    # Wait for the daemon to become responsive (up to 60 seconds)
    Write-Info "Waiting for Docker daemon to become ready..."
    $maxWait = 60
    $waited = 0
    $ready = $false
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 3
        $waited += 3
        if (Test-DockerRunning) {
            $ready = $true
            break
        }
        Write-Info "  ...still waiting ($waited s / $maxWait s)"
    }
    if (-not $ready) {
        Exit-WithError "Docker daemon did not become ready within $maxWait seconds. Start it manually and try again."
    }
}
Write-Success "Docker daemon is running"

# Node.js (needed for npx prisma)
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Exit-WithError "Node.js is not installed or not on PATH. Install it from https://nodejs.org/ and try again."
}
Write-Success "Node.js found: $(node --version)"

# docker-compose.yml
$ComposeFile = Join-Path $ProjectRoot "docker-compose.yml"
if (-not (Test-Path $ComposeFile)) {
    Exit-WithError "docker-compose.yml not found in project root: $ProjectRoot"
}
Write-Success "docker-compose.yml found"

# ---------------------------------------------------------------------------
# 2. Virtual environment
# ---------------------------------------------------------------------------

Write-Header "2 / 9  Virtual environment"

$Script:VenvDir = Join-Path $ProjectRoot ".venv"

if ($Script:OnWindows) {
    $Script:VenvBin        = Join-Path $Script:VenvDir "Scripts"
    $Script:VenvPython     = Join-Path $Script:VenvBin "python.exe"
    $Script:ActivateScript = Join-Path $Script:VenvBin "Activate.ps1"
} else {
    $Script:VenvBin        = Join-Path $Script:VenvDir "bin"
    $Script:VenvPython     = Join-Path $Script:VenvBin "python"
    $Script:ActivateScript = Join-Path $Script:VenvBin "Activate.ps1"
}

# An existing .venv directory with no python is a corrupted half-install -
# treat it as missing so we recreate cleanly.
$venvLooksValid = (Test-Path $Script:VenvDir) -and (Test-Path $Script:VenvPython)

if (-not $venvLooksValid) {
    if (Test-Path $Script:VenvDir) {
        Write-Info ".venv exists but appears incomplete - recreating"
        Remove-Item -Recurse -Force $Script:VenvDir
    }
    Write-Info "Creating .venv with uv ..."
    Push-Location $ProjectRoot
    try {
        uv venv .venv
        if ($LASTEXITCODE -ne 0) { Exit-WithError "uv venv failed." }
    } finally {
        Pop-Location
    }
    Write-Success ".venv created"
} else {
    Write-Info ".venv already exists - skipping creation"
}

if (-not (Test-Path $Script:VenvPython)) {
    Exit-WithError "Could not find venv python at: $Script:VenvPython"
}
if (-not (Test-Path $Script:ActivateScript)) {
    Exit-WithError "Could not find activation script at: $Script:ActivateScript"
}

Write-Info "Activating .venv ..."
& $Script:ActivateScript
Write-Success ".venv activated"

# ---------------------------------------------------------------------------
# 3. Python dependencies
# ---------------------------------------------------------------------------

Write-Header "3 / 9  Python dependencies"

Push-Location $ProjectRoot
try {
    $RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
    if (-not (Test-Path $RequirementsFile)) {
        Exit-WithError "requirements.txt not found at $RequirementsFile."
    }

    Write-Info "Installing requirements.txt ..."
    uv pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Exit-WithError "uv pip install -r requirements.txt failed." }

    Write-Info "Installing asyncpg and boto3 ..."
    uv pip install asyncpg boto3
    if ($LASTEXITCODE -ne 0) { Exit-WithError "uv pip install asyncpg boto3 failed." }

    # Verify chainlit is available using the venv python directly
    Write-Info "Verifying chainlit installation ..."
    & $Script:VenvPython -m chainlit --version | Out-Null
    if ($LASTEXITCODE -ne 0) { Exit-WithError "chainlit verification failed after installation." }
} finally {
    Pop-Location
}
Write-Success "Python dependencies installed"

# ---------------------------------------------------------------------------
# 4. .env setup
# ---------------------------------------------------------------------------

Write-Header "4 / 9  .env setup"

$EnvFile    = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env_example"

if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvExample)) {
        Exit-WithError ".env_example not found in project root. Cannot create .env."
    }
    Copy-Item $EnvExample $EnvFile
    Write-Info "Copied .env_example -> .env"
    Write-Host ""
    Write-Host "  !  ACTION REQUIRED: Open .env and fill in your API keys before running the agent." -ForegroundColor Magenta
} else {
    Write-Info ".env already exists - skipping copy"
}

# ---------------------------------------------------------------------------
# 5. Chainlit auth setup
# ---------------------------------------------------------------------------

Write-Header "5 / 9  Chainlit auth setup"

# Username
Write-Host ""
$ChainlitUsername = Read-Host "  Enter Chainlit username (used to login into the agent UI)"
if ([string]::IsNullOrWhiteSpace($ChainlitUsername)) {
    Exit-WithError "Username cannot be empty."
}

# Password (with confirmation loop)
while ($true) {
    $Password1 = Read-Host "  Enter Chainlit password" -AsSecureString
    $Password2 = Read-Host "  Confirm Chainlit password" -AsSecureString

    # Convert SecureString -> plain text for comparison
    $Plain1 = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password1))
    $Plain2 = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password2))

    if ($Plain1 -ceq $Plain2) {
        $ChainlitPassword = $Plain1
        break
    }
    Write-Fail "Passwords do not match. Please try again."
}

# Generate Chainlit auth secret
if (-not $Script:VenvPython -or -not (Test-Path $Script:VenvPython)) {
    Exit-WithError "Internal error: venv python is not available at this point ($Script:VenvPython)."
}

Write-Info "Generating Chainlit auth secret ..."
Push-Location $ProjectRoot
try {
    # Call chainlit via the venv python directly
    $SecretOutput = & $Script:VenvPython -m chainlit create-secret 2>&1
    $CreateSecretExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($CreateSecretExit -ne 0) {
    Exit-WithError "chainlit create-secret failed. Is chainlit installed? ($SecretOutput)"
}

# Parse: find a line containing CHAINLIT_AUTH_SECRET=
$SecretLine = ($SecretOutput | Where-Object { $_ -match "CHAINLIT_AUTH_SECRET\s*=" }) | Select-Object -First 1
if (-not $SecretLine) {
    Exit-WithError "Could not parse CHAINLIT_AUTH_SECRET from chainlit create-secret output.`nOutput was:`n$SecretOutput"
}
# Strip optional surrounding quotes from the parsed value.
$ChainlitSecret = ($SecretLine -replace "^.*CHAINLIT_AUTH_SECRET\s*=\s*", "").Trim().Trim('"').Trim("'")

# Write to .env
Set-EnvKey -FilePath $EnvFile -Key "CHAINLIT_AUTH_SECRET" -Value $ChainlitSecret
Set-EnvKey -FilePath $EnvFile -Key "CHAINLIT_USERNAME"    -Value $ChainlitUsername
Set-EnvKey -FilePath $EnvFile -Key "CHAINLIT_PASSWORD"    -Value $ChainlitPassword

Write-Success "Chainlit auth credentials written to .env"

# ---------------------------------------------------------------------------
# 6. Chainlit datalayer (postgres + localstack) - cloned into the project root
# ---------------------------------------------------------------------------

Write-Header "6 / 9  Chainlit datalayer setup"

$SettingsFile     = Join-Path $ProjectRoot "config\settings.json"
$DefaultDlDir     = Join-Path $ProjectRoot "chainlit-datalayer"
$DatalayerRepoUrl = "https://github.com/Chainlit/chainlit-datalayer.git"

# Resolve target directory: prefer existing valid value in settings.json,
# otherwise clone into the project root.
$Script:DlDir = ""
if (Test-Path $SettingsFile) {
    try {
        $settingsObj  = Get-Content $SettingsFile -Raw | ConvertFrom-Json
        $existingDl   = $settingsObj.chainlit_datalayer_dir
        if ($existingDl -and (Test-Path (Join-Path $existingDl "compose.yaml"))) {
            $Script:DlDir = (Resolve-Path $existingDl).Path
            Write-Info "Using existing chainlit-datalayer at $Script:DlDir"
        }
    } catch {
        Write-Info "Could not parse settings.json - falling back to default datalayer dir"
    }
}

if (-not $Script:DlDir) {
    if (-not (Test-Path $DefaultDlDir)) {
        Write-Info "Cloning chainlit-datalayer into $DefaultDlDir ..."
        git clone $DatalayerRepoUrl $DefaultDlDir
        if ($LASTEXITCODE -ne 0) { Exit-WithError "git clone of chainlit-datalayer failed." }
        Write-Success "chainlit-datalayer cloned"
    } else {
        Write-Info "chainlit-datalayer directory already present at $DefaultDlDir - skipping clone"
    }
    $Script:DlDir = (Resolve-Path $DefaultDlDir).Path
}

$Script:DlComposeFile = Join-Path $Script:DlDir "compose.yaml"
if (-not (Test-Path $Script:DlComposeFile)) {
    Exit-WithError "chainlit-datalayer compose file not found at $Script:DlComposeFile (clone may have failed)."
}

# Persist the resolved absolute path back into config/settings.json so
# run_agent.ps1 picks it up on subsequent launches. We use a regex replace
# rather than a JSON round-trip so we don't churn key ordering or strip
# any in-file comments the user may add later.
if (Test-Path $SettingsFile) {
    $settingsRaw = Get-Content $SettingsFile -Raw
    # JSON-escape backslashes in the path: \ -> \\
    $jsonPath = $Script:DlDir -replace '\\', '\\'
    $pattern  = '"chainlit_datalayer_dir"\s*:\s*"[^"]*"'
    $newLine  = '"chainlit_datalayer_dir": "' + $jsonPath + '"'
    if ($settingsRaw -match $pattern) {
        # Use MatchEvaluator delegate to avoid replacement-string interpretation
        $evaluator = [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $newLine }
        $settingsRaw = [System.Text.RegularExpressions.Regex]::Replace($settingsRaw, $pattern, $evaluator)
        [System.IO.File]::WriteAllText($SettingsFile, $settingsRaw, [System.Text.UTF8Encoding]::new($false))
        Write-Success "Updated chainlit_datalayer_dir in config/settings.json"
    } else {
        Write-Info "chainlit_datalayer_dir key not found in settings.json - leaving file untouched"
    }
}

# ---------------------------------------------------------------------------
# 7. Docker services (chainlit-datalayer postgres + localstack, plus MinIO)
# ---------------------------------------------------------------------------

Write-Header "7 / 9  Docker services"

# Bring up chainlit-datalayer (postgres + localstack)
Write-Info "Starting chainlit-datalayer compose project ..."
docker compose -f $Script:DlComposeFile up -d
if ($LASTEXITCODE -ne 0) { Exit-WithError "docker compose up -d for chainlit-datalayer failed." }

# Bring up this repo's compose stack (MinIO)
Push-Location $ProjectRoot
try {
    Write-Info "Starting MinIO compose project ..."
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { Exit-WithError "docker compose up -d failed for MinIO." }
} finally {
    Pop-Location
}

# Wait for MinIO
Write-Info "Waiting for MinIO to be healthy ..."
$MinioUrl  = "http://localhost:9000/minio/health/live"
$MaxWait   = 30
$Elapsed   = 0
$MinioOk   = $false

while ($Elapsed -lt $MaxWait) {
    try {
        $response = Invoke-WebRequest -Uri $MinioUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $MinioOk = $true
            break
        }
    } catch { }
    Write-Host "." -NoNewline -ForegroundColor DarkGray
    Start-Sleep -Seconds 1
    $Elapsed++
}
Write-Host ""

if (-not $MinioOk) {
    Exit-WithError "MinIO did not become healthy within ${MaxWait}s. Check `docker compose logs minio`."
}
Write-Success "MinIO is healthy"

# Wait for PostgreSQL inside the chainlit-datalayer compose project.
# pg_isready exits non-zero while the DB is still booting, which under
# $ErrorActionPreference='Stop' would otherwise escalate to a script-killing
# NativeCommandError. We wrap each poll in try/catch so transient failures
# during the wait phase are treated as 'not ready yet'.
Write-Info "Waiting for PostgreSQL to be ready ..."
$Elapsed = 0
$PgOk    = $false

while ($Elapsed -lt $MaxWait) {
    $pgExit = 1
    try {
        docker compose -f $Script:DlComposeFile exec -T postgres pg_isready *> $null
        $pgExit = $LASTEXITCODE
    } catch {
        $pgExit = 1
    }

    if ($pgExit -eq 0) {
        $PgOk = $true
        break
    }
    Write-Host "." -NoNewline -ForegroundColor DarkGray
    Start-Sleep -Seconds 1
    $Elapsed++
}
Write-Host ""

if (-not $PgOk) {
    Exit-WithError "PostgreSQL did not become ready within ${MaxWait}s. Check `docker compose -f `"$Script:DlComposeFile`" logs postgres`."
}
Write-Success "PostgreSQL is ready"

# ---------------------------------------------------------------------------
# 8. Prisma migration
# ---------------------------------------------------------------------------

Write-Header "8 / 9  Prisma migration"

# The Prisma schema lives in the chainlit-datalayer repo at prisma/schema.prisma.
# Migrations must therefore be run from inside the datalayer directory, and
# prisma reads DATABASE_URL from .env in CWD - so seed .env from .env.example
# on a fresh clone before invoking prisma.
$DlEnvFile     = Join-Path $Script:DlDir ".env"
$DlEnvExample  = Join-Path $Script:DlDir ".env.example"
if (-not (Test-Path $DlEnvFile)) {
    if (Test-Path $DlEnvExample) {
        Copy-Item $DlEnvExample $DlEnvFile
        Write-Info "Seeded chainlit-datalayer .env from .env.example"
    } else {
        Write-Info "No .env.example found in chainlit-datalayer - prisma will rely on environment variables"
    }
}

Push-Location $Script:DlDir
try {
    # chainlit-datalayer pins prisma ^6.x in its package.json; without a local
    # install, npx resolves to whatever it has cached globally (currently 7.x),
    # which has dropped support for `url`/`directUrl` in schema.prisma. Install
    # local node_modules so npx picks up the pinned 6.x bin.
    $DlNodeModules = Join-Path $Script:DlDir "node_modules"
    if (-not (Test-Path $DlNodeModules)) {
        Write-Info "Installing chainlit-datalayer node dependencies (npm install) ..."
        npm install
        if ($LASTEXITCODE -ne 0) { Exit-WithError "npm install in chainlit-datalayer failed." }
    } else {
        Write-Info "chainlit-datalayer node_modules present - skipping npm install"
    }

    Write-Info "Running npx prisma migrate deploy in $Script:DlDir ..."
    npx prisma migrate deploy
    $PrismaExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($PrismaExit -ne 0) {
    Exit-WithError "npx prisma migrate deploy failed (exit code $PrismaExit). Check the output above for details."
}
Write-Success "Prisma migrations applied"

# ---------------------------------------------------------------------------
# 9. Final summary
# ---------------------------------------------------------------------------

Write-Header "9 / 9  Setup complete"
Write-Host ""
Write-Host "  agentY is ready to go!  Here's what was set up:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  * Python .venv created and dependencies installed" -ForegroundColor White
Write-Host "  * .env created and Chainlit auth credentials written" -ForegroundColor White
Write-Host "  * chainlit-datalayer cloned at $Script:DlDir (postgres + localstack running)" -ForegroundColor White
Write-Host "  * MinIO container is running" -ForegroundColor White
Write-Host "  * Prisma migrations applied" -ForegroundColor White
Write-Host ""
Write-Host "  --- Next steps ---" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  1. Fill in remaining API keys in .env before the first run" -ForegroundColor Yellow
Write-Host "     (HF_TOKEN, ANTHROPIC_API_KEY, COMFYUI_API_KEY, etc.)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  2. Start the agent:" -ForegroundColor Yellow
Write-Host "     ./run_agent.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  3. MinIO console:  http://localhost:9001" -ForegroundColor Yellow
Write-Host "     Credentials:    minioadmin / minioadmin" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
