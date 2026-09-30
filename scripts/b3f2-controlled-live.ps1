[CmdletBinding()]
param([switch]$ConfirmPaidRun, [string]$AcceptanceId, [string]$ProjectId)
$ErrorActionPreference = 'Stop'
if (-not $ConfirmPaidRun) {
    Write-Output 'NOT RUN: explicit -ConfirmPaidRun authorization is required.'
    exit 2
}
if ([string]::IsNullOrWhiteSpace($AcceptanceId)) {
    Write-Output 'NOT RUN: an explicit -AcceptanceId is required.'
    exit 2
}
if ($AcceptanceId -notmatch '\A[A-Za-z0-9][A-Za-z0-9._-]{0,79}\z' -or $AcceptanceId.Contains('..')) {
    Write-Output 'NOT RUN: Invalid AcceptanceId.'
    exit 2
}
$windowsDeviceNamePattern = '(?i)\A(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\z'
if ($AcceptanceId -match $windowsDeviceNamePattern) {
    Write-Output 'NOT RUN: Invalid AcceptanceId.'
    exit 2
}
$reservedAcceptanceIds = @('legacy', '1', 'first', 'b3f2-real-20260930-01', 'b3f2-real-20260930-1')
if ($reservedAcceptanceIds -contains $AcceptanceId) {
    Write-Output 'NOT RUN: Invalid AcceptanceId.'
    exit 2
}
if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    Write-Output 'NOT RUN: provide an existing dedicated acceptance ProjectId.'
    exit 2
}
$taskRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $taskRoot 'backend'
# Configuration and credentials must already be in this process environment.
# Never print secrets or pass credentials as command-line arguments.
& (Join-Path $taskRoot '.venv/Scripts/python.exe') -m app.tools.b3f2_controlled_live `
    --confirm-paid-run --acceptance-id $AcceptanceId --project-id $ProjectId
exit $LASTEXITCODE
