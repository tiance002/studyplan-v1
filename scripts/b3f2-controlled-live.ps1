[CmdletBinding()]
param([switch]$ConfirmPaidRun, [string]$ProjectId)
$ErrorActionPreference = 'Stop'
if (-not $ConfirmPaidRun) {
    Write-Output 'NOT RUN: explicit -ConfirmPaidRun authorization is required.'
    exit 2
}
if (-not $ProjectId) { throw 'Provide an existing dedicated acceptance ProjectId.' }
$taskRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $taskRoot 'backend'
# Configuration and credentials must already be in this process environment.
# Never print secrets or pass credentials as command-line arguments.
& (Join-Path $taskRoot '.venv/Scripts/python.exe') -m app.tools.b3f2_controlled_live --confirm-paid-run --project-id $ProjectId
exit $LASTEXITCODE
