<#
.SYNOPSIS
    Remove the dev-stack scheduled task created by install_watchdog.ps1.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "VoiceCloningDevStart"
)

$ErrorActionPreference = "Stop"

if (-not (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
    Write-Host "[skip] no task named '$TaskName' registered." -ForegroundColor Yellow
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "✓ unregistered scheduled task '$TaskName'" -ForegroundColor Green
