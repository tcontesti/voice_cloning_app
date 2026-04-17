<#
.SYNOPSIS
    Register the "VCApp Tunnel Watchdog" Scheduled Task.

.DESCRIPTION
    Per-user task (no admin required) that runs scripts\tunnel_watchdog.ps1
    every minute. The watchdog itself is a no-op unless the activation flag
    %LOCALAPPDATA%\vcapp\tunnel_enabled.flag exists, so the task is safe to
    leave registered between sessions -- dev_stop.ps1 just removes the flag.

    dev_start.ps1 calls this script automatically on each launch (idempotent
    via unregister-then-register) so the task always reflects the latest
    watchdog source.

    Uninstall with: .\scripts\uninstall_watchdog.ps1

.PARAMETER TaskName
    Scheduled Task name (default: "VCApp Tunnel Watchdog").
#>
[CmdletBinding()]
param(
    [string]$TaskName = "VCApp Tunnel Watchdog"
)

$ErrorActionPreference = "Stop"
$Root     = Split-Path -Parent $PSScriptRoot
$Watchdog = Join-Path $Root "scripts\tunnel_watchdog.ps1"

if (-not (Test-Path $Watchdog)) { throw "tunnel_watchdog.ps1 not found at $Watchdog" }

# Always re-register so action/trigger reflect the latest script. Without this
# step a moved repo or edited tunnel_watchdog.ps1 would silently keep running
# the stale registration.
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Watchdog`""

# "Every minute, indefinitely". -RepetitionDuration must be set alongside
# -RepetitionInterval; ~10y is effectively forever for this pilot.
$start    = (Get-Date).AddSeconds(30)
$interval = New-TimeSpan -Minutes 1
$duration = New-TimeSpan -Days 3650
$trigger  = New-ScheduledTaskTrigger -Once -At $start `
    -RepetitionInterval $interval -RepetitionDuration $duration

# IgnoreNew: if a tick is still running when the next fires, skip it instead
# of queueing -- avoids stacked respawns under disk pressure.
# ExecutionTimeLimit 5m: kill the watchdog if it ever hangs (should finish
# in <1s normally).
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings `
    -Description "Respawn autossh tunnel to Spark when it dies. Gated by %LOCALAPPDATA%\vcapp\tunnel_enabled.flag." `
    | Out-Null

Write-Host "[OK] registered scheduled task '$TaskName' (every 1 min)" -ForegroundColor Green
Write-Host "  Run on demand:  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor DarkGray
Write-Host "  Inspect:        Get-ScheduledTaskInfo -TaskName '$TaskName'" -ForegroundColor DarkGray
Write-Host "  Logs:           %LOCALAPPDATA%\vcapp\logs\tunnel_watchdog.log" -ForegroundColor DarkGray
Write-Host "  Uninstall:      .\scripts\uninstall_watchdog.ps1" -ForegroundColor DarkGray
