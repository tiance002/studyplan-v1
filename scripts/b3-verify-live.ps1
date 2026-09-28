$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
foreach ($line in Get-Content -LiteralPath (Join-Path $taskRoot '.env') -Encoding utf8) {
    if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim().Trim('"').Trim("'"), 'Process') }
}
$env:PYTHONPATH = Join-Path $taskRoot 'backend'
& (Join-Path $taskRoot '.venv/Scripts/python.exe') -m app.tools.verify_b3_live @args
exit $LASTEXITCODE
