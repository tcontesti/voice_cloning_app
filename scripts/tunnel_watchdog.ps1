<#
.SYNOPSIS
    Per-minute watchdog that respawns autossh if it has died OR gone zombie
    (process alive, ssh child gone, no listening port).

.DESCRIPTION
    Designed to be invoked by the "VCApp Tunnel Watchdog" Scheduled Task
    installed via install_watchdog.ps1. Acts only when the activation flag
    %LOCALAPPDATA%\vcapp\tunnel_enabled.flag exists -- this lets dev_stop.ps1
    pause the watchdog (delete the flag) without unregistering the task.

    The flag is a JSON file written by dev_start.ps1 with the SparkAlias and
    the absolute autossh / ssh paths captured at start time, so the watchdog
    relaunches the SAME binary even if the user's PATH changed since.

    Health model: process existence is necessary but not sufficient. autossh
    on Windows can land in a zombie state where the parent process is alive
    but its ssh child has died and no port is bound. Each tick probes the
    local-side RabbitMQ forward (localhost:5682) -- if the process is up but
    the port is dead beyond a 30s grace period, the zombie is killed and a
    fresh autossh is spawned.

    Logs go to %LOCALAPPDATA%\vcapp\logs\tunnel_watchdog.log. To keep the log
    quiet enough to be useful, only state changes (respawn, zombie-kill,
    error) are written -- silent ticks mean autossh is healthy.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$AppDir       = Join-Path $env:LOCALAPPDATA "vcapp"
$LogDir       = Join-Path $AppDir "logs"
$LogFile      = Join-Path $LogDir "tunnel_watchdog.log"
$FlagPath     = Join-Path $AppDir "tunnel_enabled.flag"
$HealthPort   = 5682   # local-side RabbitMQ AMQP forward; one of the -L's in $forwards
$GraceSeconds = 30     # don't probe a freshly respawned autossh -- ssh handshake may be in flight
$TunnelPortsRx = '5682|9010|15682|9011|5433|6380'

function Write-WatchdogLog {
    param([string]$Level, [string]$Message)
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$ts [$Level] $Message" | Add-Content -LiteralPath $LogFile -Encoding UTF8
}

function Test-TunnelPort {
    param([int]$Port)
    # Test-NetConnection writes a noisy "WARNING: TCP connect failed" to the
    # warning stream when the port is closed; suppress it (we only care about
    # the bool) along with its progress bar.
    $prevWarn = $WarningPreference; $prevProg = $ProgressPreference
    $WarningPreference  = 'SilentlyContinue'
    $ProgressPreference = 'SilentlyContinue'
    try {
        return [bool](Test-NetConnection -ComputerName localhost -Port $Port `
            -InformationLevel Quiet -ErrorAction SilentlyContinue)
    } catch {
        return $false
    } finally {
        $WarningPreference  = $prevWarn
        $ProgressPreference = $prevProg
    }
}

# 1 -- disabled? exit silently so the scheduled task LastResult stays 0.
if (-not (Test-Path $FlagPath)) {
    return
}

# Read flag once; both the health check (kill path) and the respawn need it.
try {
    $flag = Get-Content -LiteralPath $FlagPath -Raw | ConvertFrom-Json
} catch {
    Write-WatchdogLog "ERROR" "could not parse $FlagPath -- $($_.Exception.Message)"
    return
}

$autosshPath = $flag.AutosshPath
$sshPath     = $flag.SshPath
$sparkAlias  = $flag.SparkAlias

# 2 -- autossh process check + tunnel health probe.
$running = Get-Process -Name autossh -ErrorAction SilentlyContinue
if ($running) {
    # Grace period: don't probe a freshly respawned autossh. If we kill+respawn
    # during ssh handshake we'll thrash forever whenever Spark is briefly
    # unreachable. The youngest start time is what matters -- a healthy autossh
    # plus a stale one would still be considered "fresh".
    $youngest = $running | Sort-Object StartTime -Descending | Select-Object -First 1
    if (((Get-Date) - $youngest.StartTime).TotalSeconds -lt $GraceSeconds) {
        return
    }

    if (Test-TunnelPort -Port $HealthPort) {
        return  # process up + port alive -> tunnel healthy
    }

    # Zombie: process up but port dead. Kill autossh AND any orphan ssh
    # children matching this spark alias -- if we leave the ssh child alive
    # it keeps the local port bound and the next autossh fails to bind.
    Write-WatchdogLog "WARN" "autossh up (PIDs $($running.Id -join ',')) but localhost:$HealthPort dead -- killing zombie and respawning"
    Stop-Process -Name autossh -Force -ErrorAction SilentlyContinue
    if ($sparkAlias) {
        Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" |
            Where-Object {
                $_.CommandLine -match $sparkAlias -and
                $_.CommandLine -match "-[LR]\s+($TunnelPortsRx)\b"
            } |
            ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
    }
    Start-Sleep -Seconds 1
}

# 3 -- (re)spawn.
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
