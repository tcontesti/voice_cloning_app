<#
.SYNOPSIS
    Unregister the "VCApp Tunnel Watchdog" Scheduled Task and remove the
    activation flag.

.DESCRIPTION
    Also cleans up the legacy "VoiceCloningDevStart" at-logon task left over
    from the previous watchdog design (auto-start dev_start.ps1 at login),
    if present, so old installs don't keep firing after upgrade.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "VCApp Tunnel Watchdog"
)

$ErrorActionPreference = "Continue"

$removed = @()
foreach ($name in @($TaskName, "VoiceCloningDevStart")) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        $removed += $name
    }
}

$flagPath = Join-Path $env:LOCALAPPDATA "vcapp\tunnel_enabled.flag"
if (Test-Path $flagPath) {
    Remove-Item -LiteralPath $flagPath -Force
    Write-Host "[OK] removed flag $flagPath" -ForegroundColor Green
}

if ($removed.Count -eq 0) {
    Write-Host "[skip] no watchdog tasks registered." -ForegroundColor Yellow
} else {
    foreach ($name in $removed) {
        Write-Host "[OK] unregistered scheduled task '$name'" -ForegroundColor Green
    }
}
