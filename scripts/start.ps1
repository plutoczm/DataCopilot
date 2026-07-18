[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 8502
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$DataTemp = Join-Path $ProjectRoot "data\temp"
$LogDir = Join-Path $ProjectRoot "data\logs"
$BackendPidFile = Join-Path $DataTemp "backend-dev.pid"
$FrontendPidFile = Join-Path $DataTemp "frontend-dev.pid"
$InstallMarker = Join-Path $VenvDir ".datacopilot-deps"

function Find-Python {
    foreach ($candidate in @("py", "python3", "python")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        try {
            $version = & $candidate --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $version -match "Python") { return $candidate }
        } catch { }
    }
    throw "No usable Python found. Install Python 3.12+ and run this script again."
}

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$Arguments,
        [string]$LogPath,
        [hashtable]$Environment = @{}
    )
    $pidFile = if ($Name -eq "backend") { $BackendPidFile } else { $FrontendPidFile }
    if (Test-Path $pidFile) {
        $existingPid = [int](Get-Content $pidFile -Raw).Trim()
        if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
            Write-Host "$Name is already running. PID=$existingPid"
            return $existingPid
        }
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    }

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $VenvPython
    $startInfo.Arguments = $Arguments
    $startInfo.WorkingDirectory = $ProjectRoot
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($entry in $Environment.GetEnumerator()) { $startInfo.Environment[$entry.Key] = [string]$entry.Value }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $process.Start() | Out-Null
    $process.add_OutputDataReceived({ param($sender, $event) if ($null -ne $event.Data) { Add-Content -LiteralPath $LogPath -Value $event.Data } })
    $process.add_ErrorDataReceived({ param($sender, $event) if ($null -ne $event.Data) { Add-Content -LiteralPath $LogPath -Value $event.Data } })
    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()
    Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii
    Write-Host "$Name started. PID=$($process.Id)"
    return $process.Id
}

New-Item -ItemType Directory -Force -Path $DataTemp, $LogDir | Out-Null
foreach ($directory in @("data\cache", "data\uploads", "data\chromadb", "data\embeddings")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot $directory) | Out-Null
}

$pythonCommand = Find-Python
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Windows virtual environment..."
    & $pythonCommand -m venv $VenvDir
}
if (-not (Test-Path $VenvPython)) { throw "Failed to create virtual environment: $VenvPython" }

if (-not $SkipInstall -and -not (Test-Path $InstallMarker)) {
    Write-Host "Installing project dependencies (the first run may take a few minutes)..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $ProjectRoot "backend\requirements.txt") -r (Join-Path $ProjectRoot "frontend\requirements.txt") -r (Join-Path $ProjectRoot "requirements-dev.txt")
    Set-Content -LiteralPath $InstallMarker -Value (Get-Date).ToString("o") -Encoding ascii
}
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot ".env.example") -Destination (Join-Path $ProjectRoot ".env")
    Write-Host "Created .env from .env.example. Fill DEEPSEEK_API_KEY for AI features."
}

$backendLog = Join-Path $LogDir "backend-dev.log"
$frontendLog = Join-Path $LogDir "frontend-dev.log"
$backendPid = Start-ServiceProcess -Name "backend" -Arguments "-m uvicorn backend.app.main:app --host 0.0.0.0 --port $BackendPort" -LogPath $backendLog
$frontendPid = Start-ServiceProcess -Name "frontend" -Arguments "-m streamlit run frontend/app.py --server.address 0.0.0.0 --server.port $FrontendPort --server.headless true --browser.gatherUsageStats false" -LogPath $frontendLog -Environment @{ BACKEND_URL = "http://127.0.0.1:$BackendPort" }

Write-Host ""
Write-Host "DataPilot-AI started:"
Write-Host "  Web UI:  http://127.0.0.1:$FrontendPort"
Write-Host "  API:     http://127.0.0.1:$BackendPort/docs"
Write-Host "  Logs:    $LogDir"
Write-Host "Stop:     .\scripts\stop.ps1"
