<#
.SYNOPSIS
    Stop the dev multi-host stack: docker + SSH tunnel(s) to Spark.
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

Write-Host "[2/2] killing SSH tunnels to '$SparkAlias' ..." -ForegroundColor Cyan
Get-CimInstance Win32_Process -Filter "Name = 'ssh.exe'" |
    Where-Object { $_.CommandLine -match "-L\s+5672" -and $_.CommandLine -match $SparkAlias } |
    ForEach-Object {
        Write-Host "  stopping PID $($_.ProcessId)" -ForegroundColor DarkGray
        Stop-Process -Id $_.ProcessId -Force
    }

Write-Host "✓ dev multi-host stopped" -ForegroundColor Green
