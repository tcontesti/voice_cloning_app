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
# autossh on Windows wraps an inner ssh.exe; kill both. Filter by the forwarded
# ports so we don't touch unrelated ssh sessions on the same host.
$tunnelNames = @('autossh.exe', 'ssh.exe')
foreach ($name in $tunnelNames) {
    Get-CimInstance Win32_Process -Filter "Name = '$name'" |
        Where-Object {
            $_.CommandLine -match "-[LR]\s+\d" -and $_.CommandLine -match $SparkAlias
        } |
        ForEach-Object {
            Write-Host "  stopping $name PID $($_.ProcessId)" -ForegroundColor DarkGray
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

Write-Host "✓ dev multi-host stopped" -ForegroundColor Green
