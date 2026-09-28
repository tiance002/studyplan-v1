param([switch]$Frontend)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $taskRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) { throw 'Create .env from .env.example first.' }
foreach ($line in Get-Content -LiteralPath $envFile -Encoding utf8) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
if ($Frontend) {
    Push-Location (Join-Path $taskRoot 'frontend')
    try { npm run dev -- --host 127.0.0.1 } finally { Pop-Location }
} else {
    $env:PYTHONPATH = Join-Path $taskRoot 'backend'
    & (Join-Path $taskRoot '.venv/Scripts/python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
