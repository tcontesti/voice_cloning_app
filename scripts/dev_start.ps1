<#
.SYNOPSIS
    Start dev multi-host stack on Windows: SSH tunnel → Spark + local docker + frontend HMR.

.DESCRIPTION
    One-shot bootstrap for the private pilot:
      1. Opens an SSH tunnel to Spark for RabbitMQ (5672) and MinIO (9000).
      2. Builds and starts Postgres + Redis + Backend + nginx on the PC.
      3. Starts the Vite dev server in a new PowerShell window.

    The tunnel process PID is printed so you can kill it manually; when you
    stop the docker stack (`docker compose down` or Ctrl-C on dev_stop.ps1)
    the tunnel keeps running until you stop it.

.PARAMETER SparkAlias
    SSH host alias (default: "spark"). Must work without password prompt.

.EXAMPLE
    .\scripts\dev_start.ps1
#>
[CmdletBinding()]
param(
    [string]$SparkAlias = "spark"
)

$ErrorActionPreference = "Stop"
$Root        = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "infra\compose\docker-compose.multihost.yml"
$EnvFile     = Join-Path $Root "infra\compose\.env.multihost"
$EnvExample  = "$EnvFile.example"

Set-Location $Root

# 0 — env file
if (-not (Test-Path $EnvFile)) {
    Write-Host "[setup] .env.multihost missing — copying from example" -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
    Write-Host "[setup] edit $EnvFile to match Spark's RabbitMQ / MinIO creds, then rerun." -ForegroundColor Yellow
    exit 1
}

# 1 — SSH tunnel (hidden, persistent)
Write-Host "[1/3] opening SSH tunnel to '$SparkAlias' (5672, 9000) ..." -ForegroundColor Cyan
$sshArgs = @(
    "-N",
    "-o", "ServerAliveInterval=30",
    "-o", "ExitOnForwardFailure=yes",
    "-L", "5672:localhost:5672",
    "-L", "9000:localhost:9000",
    $SparkAlias
)
$ssh = Start-Process ssh -ArgumentList $sshArgs -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
if ($ssh.HasExited) {
    throw "SSH tunnel exited immediately. Check that 'ssh $SparkAlias' works without a password prompt."
}
Write-Host "      tunnel PID=$($ssh.Id) (kill with: Stop-Process $($ssh.Id))" -ForegroundColor DarkGray

# 2 — docker stack
Write-Host "[2/3] docker compose up --build ..." -ForegroundColor Cyan
docker compose -f $ComposeFile --env-file $EnvFile up -d --build
if ($LASTEXITCODE -ne 0) {
    Stop-Process $ssh.Id -ErrorAction SilentlyContinue
    throw "docker compose failed (exit $LASTEXITCODE). Tunnel stopped."
}

# 3 — frontend Vite HMR in a new window
Write-Host "[3/3] starting Vite dev server in a new window ..." -ForegroundColor Cyan
$frontendDir = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "      (first run: installing npm deps — this will take a minute)" -ForegroundColor DarkGray
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm install; npm run dev"
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"
}

Write-Host ""
Write-Host "✓ dev multi-host up" -ForegroundColor Green
Write-Host "  Backend:    http://localhost:8000/health"
Write-Host "  Nginx TLS:  https://localhost/"
Write-Host "  Frontend:   http://localhost:5173"
Write-Host "  SSH tunnel: PID $($ssh.Id)"
Write-Host ""
Write-Host "To stop: .\scripts\dev_stop.ps1" -ForegroundColor DarkGray
