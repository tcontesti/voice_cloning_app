<#
.SYNOPSIS
    Start dev multi-host stack on Windows: SSH tunnel -> Spark + local docker + frontend HMR.

.DESCRIPTION
    One-shot bootstrap for the private pilot:
      1. Opens a persistent tunnel to Spark (autossh preferred, ssh fallback).
         autossh reconnects automatically when the Spark host roams between
         networks or suspends overnight.
      2. Builds and starts Postgres + Redis + Backend + nginx on the PC.
      3. Starts the Vite dev server in a new PowerShell window.

    The tunnel process PID is printed so you can kill it manually; when you
    stop the docker stack (`docker compose down` or Ctrl-C on dev_stop.ps1)
    the tunnel keeps running until you stop it.

.PARAMETER SparkAlias
    SSH host alias (default: "spark"). Must work without password prompt.

.PARAMETER UseSSH
    Force plain ssh even if autossh is installed (debugging).

.EXAMPLE
    .\scripts\dev_start.ps1
#>
[CmdletBinding()]
param(
    [string]$SparkAlias = "spark",
    [switch]$UseSSH
)

$ErrorActionPreference = "Stop"
$Root        = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "infra\compose\docker-compose.multihost.yml"
$EnvFile     = Join-Path $Root "infra\compose\.env.multihost"
$EnvExample  = "$EnvFile.example"

Set-Location $Root

# 0 -- env file
if (-not (Test-Path $EnvFile)) {
    Write-Host "[setup] .env.multihost missing -- copying from example" -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
    Write-Host "[setup] edit $EnvFile to match Spark's RabbitMQ / MinIO creds, then rerun." -ForegroundColor Yellow
    exit 1
}

# 1 -- Tunnel (autossh preferred, ssh fallback)
$autossh = Get-Command autossh -ErrorAction SilentlyContinue
$useAutossh = ($autossh -ne $null) -and (-not $UseSSH)

# Port-forward spec shared by both paths. Keeping it in one list avoids drift.
$forwards = @(
    "-L", "5682:localhost:5672",    # RabbitMQ AMQP
    "-L", "9010:localhost:9000",    # MinIO S3 API
    "-L", "15682:localhost:15672",  # RabbitMQ mgmt UI
    "-L", "9011:localhost:9001",    # MinIO console
    # Reverse forwards: Spark workers dial PC-side Postgres + Redis via these.
    # If they collide with an orphan bind on Spark (previous ssh session not
    # reaped), the ExitOnForwardFailure flag below would have killed ssh and
    # autossh would loop forever — so we deliberately don't set that flag.
    # In practice when the orphan times out (sshd ClientAlive on Spark) the
    # next autossh retry binds cleanly.
    "-R", "5433:localhost:5432",    # PC Postgres -> Spark
    "-R", "6380:localhost:6379"     # PC Redis    -> Spark (Celery result backend)
)
$commonOpts = @(
    "-N",
    # 30s * 3 misses = ~90s before autossh notices and reconnects. The old
    # 15s value double-fired on transient LTE blips (laptop -> phone tether)
    # and kicked the tunnel while the link was only briefly noisy. The Spark
    # side of this pair must stay slightly more permissive (sshd
    # ClientAliveInterval=30, ClientAliveCountMax=2 -> 60s) so it reaps
    # half-open sessions before autossh's next retry attempt.
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=3",
    # Intentionally NOT setting ExitOnForwardFailure — see comment on -R above.
    # ServerAlive* still detects a dead transport and triggers autossh restart.
    "-o", "ConnectTimeout=10",
    "-o", "StrictHostKeyChecking=accept-new"
)

if ($useAutossh) {
    Write-Host "[1/3] opening autossh tunnel to '$SparkAlias' (auto-reconnect) ..." -ForegroundColor Cyan
    # AUTOSSH_GATETIME=0 means "never give up"; on first failure retry immediately.
    $env:AUTOSSH_GATETIME = "0"
    # scoop's autossh is an msys build; without AUTOSSH_PATH it looks for
    # /usr/bin/ssh (doesn't exist on Windows) and exits instantly. Point it
    # at the Windows OpenSSH binary explicitly.
    $sshWin = (Get-Command ssh -ErrorAction SilentlyContinue).Source
    if ($sshWin) { $env:AUTOSSH_PATH = $sshWin }
    $tunnelArgs = @("-M", "0") + $commonOpts + $forwards + @($SparkAlias)
    $tunnel = Start-Process autossh -ArgumentList $tunnelArgs -PassThru -WindowStyle Hidden
    $tunnelName = "autossh"
} else {
    if (-not $UseSSH) {
        Write-Host "[setup] autossh not found -- falling back to plain ssh." -ForegroundColor Yellow
        Write-Host "        Tunnel will NOT auto-reconnect if Spark roams or sleeps." -ForegroundColor Yellow
        Write-Host "        Install: scoop install autossh   (or winget install eternallybored.autossh)" -ForegroundColor DarkGray
    }
    Write-Host "[1/3] opening ssh tunnel to '$SparkAlias' ..." -ForegroundColor Cyan
    $tunnelArgs = $commonOpts + $forwards + @($SparkAlias)
    $tunnel = Start-Process ssh -ArgumentList $tunnelArgs -PassThru -WindowStyle Hidden
    $tunnelName = "ssh"
}

Start-Sleep -Seconds 2
if ($tunnel.HasExited) {
    throw "$tunnelName tunnel exited immediately. Check that 'ssh $SparkAlias' works without a password prompt."
}
Write-Host "      $tunnelName PID=$($tunnel.Id) (kill with: Stop-Process $($tunnel.Id))" -ForegroundColor DarkGray

# 2 -- docker stack
Write-Host "[2/3] docker compose up --build ..." -ForegroundColor Cyan
docker compose -f $ComposeFile --env-file $EnvFile up -d --build
if ($LASTEXITCODE -ne 0) {
    Stop-Process $tunnel.Id -ErrorAction SilentlyContinue
    throw "docker compose failed (exit $LASTEXITCODE). Tunnel stopped."
}

# 3 -- frontend Vite HMR in a new window
Write-Host "[3/3] starting Vite dev server in a new window ..." -ForegroundColor Cyan
$frontendDir = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "      (first run: installing npm deps -- this will take a minute)" -ForegroundColor DarkGray
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm install; npm run dev"
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"
}

Write-Host ""
Write-Host "[OK] dev multi-host up" -ForegroundColor Green
Write-Host "  Backend:    http://localhost:8000/health"
Write-Host "  Nginx TLS:  https://localhost/"
Write-Host "  Frontend:   http://localhost:5173"
Write-Host "  Tunnel:     $tunnelName PID $($tunnel.Id)"
Write-Host ""
Write-Host "To stop: .\scripts\dev_stop.ps1" -ForegroundColor DarkGray
