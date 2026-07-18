[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 8502
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CondaEnvDir = Join-Path $ProjectRoot ".conda"
$CondaPython = Join-Path $CondaEnvDir "python.exe"
$DataTemp = Join-Path $ProjectRoot "data\temp"
$LogDir = Join-Path $ProjectRoot "data\logs"
$BackendPidFile = Join-Path $DataTemp "backend-dev.pid"
$FrontendPidFile = Join-Path $DataTemp "frontend-dev.pid"
$InstallMarker = Join-Path $CondaEnvDir ".datacopilot-deps"

function Find-Conda {
    $candidates = @(
        $env:CONDA_EXE,
        "D:\Anaconda\Miniconda3\Scripts\conda.exe",
        "D:\Anaconda\Anaconda3\Scripts\conda.exe",
        (Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe")
    )
    $command = Get-Command conda -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw "Conda not found. Expected: D:\Anaconda\Miniconda3\Scripts\conda.exe"
}

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [hashtable]$Environment = @{}
    )

    $pidFile = if ($Name -eq "backend") { $BackendPidFile } else { $FrontendPidFile }
    if (Test-Path $pidFile) {
        $existingProcessId = [int](Get-Content $pidFile -Raw).Trim()
        if (Get-Process -Id $existingProcessId -ErrorAction SilentlyContinue) {
            Write-Host "$Name is already running. PID=$existingProcessId"
            return $existingProcessId
        }
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    }

    $savedEnvironment = @{}
    foreach ($entry in $Environment.GetEnumerator()) {
        $savedEnvironment[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, "Process")
        [Environment]::SetEnvironmentVariable($entry.Key, [string]$entry.Value, "Process")
    }
    try {
        $startParameters = @{
            FilePath = $CondaPython
            ArgumentList = $Arguments
            WorkingDirectory = $ProjectRoot
            WindowStyle = "Hidden"
            RedirectStandardOutput = (Join-Path $LogDir "$Name-dev.stdout.log")
            RedirectStandardError = (Join-Path $LogDir "$Name-dev.stderr.log")
            PassThru = $true
        }
        $process = Start-Process @startParameters
    } finally {
        foreach ($entry in $savedEnvironment.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
        }
    }

    Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
    Write-Host "$Name started. PID=$($process.Id)"
    return $process.Id
}

New-Item -ItemType Directory -Force -Path $DataTemp, $LogDir | Out-Null
foreach ($directory in @(
    "data\cache\conda\pkgs",
    "data\cache\pip",
    "data\uploads",
    "data\chromadb",
    "data\embeddings"
)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot $directory) | Out-Null
}

$env:CONDA_PKGS_DIRS = Join-Path $ProjectRoot "data\cache\conda\pkgs"
$env:PIP_CACHE_DIR = Join-Path $ProjectRoot "data\cache\pip"
$env:TEMP = $DataTemp
$env:TMP = $DataTemp

$CondaExe = Find-Conda
if (-not (Test-Path $CondaPython)) {
    Write-Host "Creating Conda environment in $CondaEnvDir with Python 3.11..."
    & $CondaExe create --prefix $CondaEnvDir python=3.11 pip -y
    if ($LASTEXITCODE -ne 0) { throw "Conda environment creation failed." }
}
if (-not (Test-Path $CondaPython)) { throw "Conda Python not found: $CondaPython" }

$needsInstall = -not (Test-Path $InstallMarker)
if (-not $needsInstall) {
    & $CondaPython -c "import chromadb, fastapi, streamlit, uvicorn" 2>$null
    $needsInstall = $LASTEXITCODE -ne 0
}

if ($needsInstall -and $SkipInstall) {
    throw "Dependencies are missing. Run start.bat without -SkipInstall."
}

if ($needsInstall) {
    Write-Host "Installing project dependencies (first run may take a few minutes)..."
    & $CondaPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
    $pipArguments = @(
        "-m", "pip", "install",
        "-r", (Join-Path $ProjectRoot "backend\requirements.txt"),
        "-r", (Join-Path $ProjectRoot "frontend\requirements.txt"),
        "-r", (Join-Path $ProjectRoot "requirements-dev.txt")
    )
    & $CondaPython @pipArguments
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    & $CondaPython -c "import chromadb, fastapi, streamlit, uvicorn"
    if ($LASTEXITCODE -ne 0) { throw "Dependency verification failed." }
    Set-Content -LiteralPath $InstallMarker -Value (Get-Date).ToString("o") -Encoding ascii
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot ".env.example") -Destination (Join-Path $ProjectRoot ".env")
    Write-Host "Created .env from .env.example. Fill DEEPSEEK_API_KEY for AI features."
}

$backendPid = Start-ServiceProcess -Name "backend" -Arguments @(
    "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort"
)
$frontendPid = Start-ServiceProcess -Name "frontend" -Arguments @(
    "-m", "streamlit", "run", "frontend/app.py",
    "--server.address", "0.0.0.0",
    "--server.port", "$FrontendPort",
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false"
) -Environment @{ BACKEND_URL = "http://127.0.0.1:$BackendPort" }

Start-Sleep -Seconds 2
if (-not (Get-Process -Id $backendPid -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $frontendPid -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $BackendPidFile, $FrontendPidFile -Force -ErrorAction SilentlyContinue
    throw "Backend exited. Check data\logs\backend-dev.stderr.log"
}
if (-not (Get-Process -Id $frontendPid -ErrorAction SilentlyContinue)) {
    Stop-Process -Id $backendPid -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $BackendPidFile, $FrontendPidFile -Force -ErrorAction SilentlyContinue
    throw "Frontend exited. Check data\logs\frontend-dev.stderr.log"
}

Write-Host ""
Write-Host "DataPilot-AI started with Conda:"
Write-Host "  Web UI:  http://127.0.0.1:$FrontendPort"
Write-Host "  API:     http://127.0.0.1:$BackendPort/docs"
Write-Host "  Conda:   $CondaEnvDir"
Write-Host "  Logs:    $LogDir"
Write-Host "Stop:     .\stop.bat"
