$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidDir = Join-Path $ProjectRoot "data\temp"

foreach ($entry in @(@("frontend", "frontend-dev.pid"), @("backend", "backend-dev.pid"))) {
    $name = $entry[0]
    $pidFile = Join-Path $PidDir $entry[1]
    if (-not (Test-Path $pidFile)) { Write-Host "$name is not running."; continue }
    $processId = [int](Get-Content $pidFile -Raw).Trim()
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $processId -Force
        Write-Host "Stopped $name. PID=$processId"
    } else { Write-Host "$name PID=$processId has already exited." }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
