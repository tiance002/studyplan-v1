param(
    [switch]$Frontend, [switch]$Demo, [switch]$Migrate, [switch]$Worker,
    [ValidateRange(1, 65535)][int]$ApiPort = 8022,
    [ValidateRange(1, 65535)][int]$FrontendPort = 5175
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
foreach ($line in Get-Content -LiteralPath (Join-Path $taskRoot '.env') -Encoding utf8) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
$env:PYTHONPATH = Join-Path $taskRoot 'backend'
$taskFrontendOrigin = "http://127.0.0.1:$FrontendPort"
$taskOrigins = @($env:ALLOW_ORIGINS -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$env:ALLOW_ORIGINS = (@($taskOrigins + $taskFrontendOrigin) | Select-Object -Unique) -join ','
if ($Demo) { $env:LLM_PROVIDER = 'fake'; $env:APP_ENV = 'development' }
if ($Migrate) {
    Push-Location (Join-Path $taskRoot 'backend')
    try { & (Join-Path $taskRoot '.venv/Scripts/python.exe') -m alembic upgrade head } finally { Pop-Location }
} elseif ($Frontend) {
    $env:STUDYPLAN_API_URL = "http://127.0.0.1:$ApiPort"
    Push-Location (Join-Path $taskRoot 'frontend')
    try { npm run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort } finally { Pop-Location }
} elseif ($Worker) {
    Push-Location (Join-Path $taskRoot 'backend')
    try { & (Join-Path $taskRoot '.venv/Scripts/python.exe') -m app.tools.planning_worker } finally { Pop-Location }
} else {
    & (Join-Path $taskRoot '.venv/Scripts/python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port $ApiPort
}
