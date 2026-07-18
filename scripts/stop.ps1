$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidDir = Join-Path $ProjectRoot "data\temp"

foreach ($entry in @(@("frontend", "frontend-dev.pid"), @("backend", "backend-dev.pid"))) {
    $name = $entry[0]
    $pidFile = Join-Path $PidDir $entry[1]
    if (-not (Test-Path $pidFile)) { Write-Host "$name is not running."; continue }
    $pid = [int](Get-Content $pidFile -Raw).Trim()
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $pid -Force
        Write-Host "Stopped $name. PID=$pid"
    } else { Write-Host "$name PID=$pid has already exited." }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
