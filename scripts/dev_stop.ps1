<#
.SYNOPSIS
    Stop the dev multi-host stack: docker + autossh/ssh tunnel(s) to Spark.
#>
[CmdletBinding()]
param(
    [string]$SparkAlias = "spark"
)

$ErrorActionPreference = "Continue"
$Root        = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "infra\compose\docker-compose.multihost.yml"
$EnvFile     = Join-Path $Root "infra\compose\.env.multihost"

Set-Location $Root

Write-Host "[1/2] docker compose down ..." -ForegroundColor Cyan
docker compose -f $ComposeFile --env-file $EnvFile down | Out-Null

Write-Host "[2/2] killing tunnels to '$SparkAlias' ..." -ForegroundColor Cyan
# autossh on Windows wraps an inner ssh.exe; kill both. A generic `-[LR]\s+\d`
# filter plus SparkAlias used to match ANY ssh-to-spark session the user had
# open (a non-tunnel shell to poke at logs, for example). Tighten by requiring
# one of the specific forwarded ports dev_start.ps1 binds, so nothing else
# gets killed even if someone has a vanilla ssh to spark running.
$tunnelPortsRegex = '5682|9010|15682|9011|5433|6380'
$tunnelNames = @('autossh.exe', 'ssh.exe')
foreach ($name in $tunnelNames) {
    Get-CimInstance Win32_Process -Filter "Name = '$name'" |
        Where-Object {
            $_.CommandLine -match $SparkAlias -and
            $_.CommandLine -match "-[LR]\s+($tunnelPortsRegex)\b"
        } |
        ForEach-Object {
            Write-Host "  stopping $name PID $($_.ProcessId)" -ForegroundColor DarkGray
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

Write-Host "[OK] dev multi-host stopped" -ForegroundColor Green
