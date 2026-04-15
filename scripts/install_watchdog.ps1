<#
.SYNOPSIS
    Register a Windows Scheduled Task that launches dev_start.ps1 at logon.

.DESCRIPTION
    Off by default — opt in by running this script explicitly. Registers a
    per-user task (no admin required) that runs scripts\dev_start.ps1 hidden
    when the user signs in. Handy for the developer workstation that always
    sits next to the Spark.

    Uninstall with: .\scripts\uninstall_watchdog.ps1

.PARAMETER TaskName
    Scheduled Task name (default: VoiceCloningDevStart).

.EXAMPLE
    .\scripts\install_watchdog.ps1
#>
[CmdletBinding()]
param(
    [string]$TaskName = "VoiceCloningDevStart"
)

$ErrorActionPreference = "Stop"
$Root      = Split-Path -Parent $PSScriptRoot
$DevStart  = Join-Path $Root "scripts\dev_start.ps1"

if (-not (Test-Path $DevStart)) { throw "dev_start.ps1 not found at $DevStart" }

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "[skip] task '$TaskName' already exists. Unregister first." -ForegroundColor Yellow
    exit 0
}

# Run hidden so the user doesn't get a popping shell on every login. The
# script itself opens its own windows where appropriate.
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$DevStart`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Auto-start voice_cloning_app dev tunnel + stack at logon."

Write-Host "✓ registered scheduled task '$TaskName'" -ForegroundColor Green
Write-Host "  Run on demand:  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor DarkGray
Write-Host "  Inspect:        Get-ScheduledTask -TaskName $TaskName | Format-List *" -ForegroundColor DarkGray
Write-Host "  Uninstall:      .\scripts\uninstall_watchdog.ps1" -ForegroundColor DarkGray
