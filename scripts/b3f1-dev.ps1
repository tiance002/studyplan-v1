param([switch]$Frontend, [switch]$Demo, [switch]$Migrate)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
foreach ($line in Get-Content -LiteralPath (Join-Path $taskRoot '.env') -Encoding utf8) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
$env:PYTHONPATH = Join-Path $taskRoot 'backend'
if ($Demo) { $env:LLM_PROVIDER = 'fake'; $env:APP_ENV = 'development' }
if ($Migrate) {
    Push-Location (Join-Path $taskRoot 'backend')
    try { & (Join-Path $taskRoot '.venv/Scripts/python.exe') -m alembic upgrade head } finally { Pop-Location }
} elseif ($Frontend) {
    Push-Location (Join-Path $taskRoot 'frontend')
    try { npm run dev -- --host 127.0.0.1 } finally { Pop-Location }
} else {
    & (Join-Path $taskRoot '.venv/Scripts/python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
