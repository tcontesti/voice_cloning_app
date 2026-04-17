<#
.SYNOPSIS
    Per-minute watchdog that respawns autossh if it has died.

.DESCRIPTION
    Designed to be invoked by the "VCApp Tunnel Watchdog" Scheduled Task
    installed via install_watchdog.ps1. Acts only when the activation flag
    %LOCALAPPDATA%\vcapp\tunnel_enabled.flag exists -- this lets dev_stop.ps1
    pause the watchdog (delete the flag) without unregistering the task.

    The flag is a JSON file written by dev_start.ps1 with the SparkAlias and
    the absolute autossh / ssh paths captured at start time, so the watchdog
    relaunches the SAME binary even if the user's PATH changed since.

    Logs go to %LOCALAPPDATA%\vcapp\logs\tunnel_watchdog.log. To keep the log
    quiet enough to be useful, only state changes (respawn, error) are
    written -- silent ticks mean autossh is up and nothing was done.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$AppDir   = Join-Path $env:LOCALAPPDATA "vcapp"
$LogDir   = Join-Path $AppDir "logs"
$LogFile  = Join-Path $LogDir "tunnel_watchdog.log"
$FlagPath = Join-Path $AppDir "tunnel_enabled.flag"

function Write-WatchdogLog {
    param([string]$Level, [string]$Message)
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$ts [$Level] $Message" | Add-Content -LiteralPath $LogFile -Encoding UTF8
}

# 1 -- disabled? exit silently so the scheduled task LastResult stays 0.
if (-not (Test-Path $FlagPath)) {
    return
}

# 2 -- autossh already up? nothing to do, no log noise.
$running = Get-Process -Name autossh -ErrorAction SilentlyContinue
if ($running) {
    return
}

# 3 -- down: read flag, respawn.
try {
    $flag = Get-Content -LiteralPath $FlagPath -Raw | ConvertFrom-Json
} catch {
    Write-WatchdogLog "ERROR" "could not parse $FlagPath -- $($_.Exception.Message)"
    return
}

$autosshPath = $flag.AutosshPath
$sshPath     = $flag.SshPath
$sparkAlias  = $flag.SparkAlias

if (-not $autosshPath -or -not (Test-Path $autosshPath)) {
    Write-WatchdogLog "ERROR" "autossh binary missing at '$autosshPath'; aborting respawn"
    return
}
if (-not $sparkAlias) {
    Write-WatchdogLog "ERROR" "SparkAlias not set in flag; aborting respawn"
    return
}

# Forwards must match scripts/dev_start.ps1 EXACTLY. There is no shared
# library for this list -- if you change one, change the other.
$forwards = @(
    "-L", "5682:localhost:5672",
    "-L", "9010:localhost:9000",
    "-L", "15682:localhost:15672",
    "-L", "9011:localhost:9001",
    "-R", "5433:localhost:5432",
    "-R", "6380:localhost:6379"
)
$commonOpts = @(
    "-N",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    "-o", "ConnectTimeout=10",
    "-o", "StrictHostKeyChecking=accept-new"
)

$env:AUTOSSH_GATETIME = "0"
if ($sshPath) { $env:AUTOSSH_PATH = $sshPath }

$tunnelArgs = @("-M", "0") + $commonOpts + $forwards + @($sparkAlias)
try {
    $proc = Start-Process -FilePath $autosshPath -ArgumentList $tunnelArgs `
        -PassThru -WindowStyle Hidden
    Write-WatchdogLog "INFO" "autossh down -> respawned PID=$($proc.Id) alias=$sparkAlias"
} catch {
    Write-WatchdogLog "ERROR" "Start-Process autossh failed: $($_.Exception.Message)"
}
