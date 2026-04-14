# Dev multi-host — PC (Windows) + Spark (GPU)

Piloto técnico privado. **No despliegue hospitalario** — la arquitectura con VPN, CA interna, Keycloak, Vault y demás se plantea cuando pasemos a v0.3.

## Topología

```
┌─────────────────────────┐          ┌──────────────────────────────┐
│  Windows PC (tu máquina)│          │  Spark (inferencia GPU)      │
│                         │          │                              │
│  Docker Desktop:        │          │  Docker Compose:             │
│   • postgres            │          │   • rabbitmq  (5672)         │
│   • redis               │          │   • minio     (9000)         │
│   • backend FastAPI     │          │                              │
│   • nginx (TLS autofir) │          │  systemd --user (native):    │
│                         │          │   • worker_chatterbox        │
│  Vite dev (npm run dev) │          │   • worker_omnivoice         │
│   :5173 (HMR)           │          │   • worker_qwen3             │
│                         │          │                              │
│        ssh -L 5672:,9000┼─────────▶│  (SSH tunnel, host loopback) │
└─────────────────────────┘          └──────────────────────────────┘
```

Datos clínicos (Postgres, audit chain) viven en tu PC. Los WAVs viven en MinIO de Spark y la cola de jobs en RabbitMQ de Spark — el backend en tu PC los alcanza vía SSH tunnel.

## Prerrequisitos

- Windows con Docker Desktop + OpenSSH (incluido desde Win10 1809).
- Node 20+ para el frontend Vite.
- Alias SSH `spark` funcionando sin password prompt (clave en `~\.ssh\config` o `ssh-agent`).
- En Spark: `voice_cloning_app` clonado, `make up` funcionando con RabbitMQ+MinIO.

## Arranque en 5 comandos

```powershell
# 0. (una vez) crear el env local con las credenciales
cp infra\compose\.env.multihost.example infra\compose\.env.multihost
notepad infra\compose\.env.multihost
# ↑ poner los MISMOS valores de RABBITMQ_* y MINIO_* que hay en
#   spark:~/voice_cloning_app/.env para que el tunnel empareje credenciales

# 1. (en Spark, una vez) dejar corriendo el stack + workers
ssh spark "cd voice_cloning_app && make up"
ssh spark "systemctl --user enable --now worker_chatterbox worker_omnivoice worker_qwen3"

# 2. (en PC, cada vez que empieces a trabajar) arrancar tunnel + docker + Vite
.\scripts\dev_start.ps1

# 3. abrir navegador
start http://localhost:5173

# 4. cuando termines
.\scripts\dev_stop.ps1
```

## Verificación rápida

Desde el PC:

```powershell
# El túnel llega
nc -vz localhost 5672         # o: Test-NetConnection localhost -Port 5672

# Backend vivo
curl http://localhost:8000/health

# Primera vez: migrar + seed
docker compose -f infra\compose\docker-compose.multihost.yml --env-file infra\compose\.env.multihost exec backend alembic upgrade head
docker compose -f infra\compose\docker-compose.multihost.yml --env-file infra\compose\.env.multihost exec backend python -m scripts.seed_users
```

Desde el navegador en `http://localhost:5173` → login con `paciente@hsll.es / paciente`, sube una referencia, genera una síntesis. Si llega a `done` con el watermark verificado, el flujo extremo-a-extremo funciona.

## Troubleshooting

**`SSH tunnel exited immediately`** — el alias `spark` pide contraseña. Configura una key en `ssh-agent` o `~\.ssh\config` con `IdentityFile`.

**Backend: `connection refused` a rabbit/minio** — el tunnel se cayó. `dev_stop.ps1` y re-arranca, o verifica `Get-Process ssh | Select-Object Id, CommandLine`.

**Worker no consume jobs** — en Spark: `journalctl --user -u worker_chatterbox -f`. Si aparece `RABBITMQ_HOST=rabbitmq` (hostname Docker), actualiza `start_worker.sh` a HEAD — ya fuerza `localhost` con override por env.

**`host.docker.internal` no resuelve (Linux)** — el compose ya lleva `extra_hosts: host.docker.internal:host-gateway`. En Windows Docker Desktop es nativo.

**Frontend no ve la API** — comprueba `VITE_API_BASE=http://localhost:8000` en `frontend\.env.local` (o déjalo vacío, el proxy Vite va por defecto a `localhost:8000`).

## Notas de seguridad del piloto

- Credenciales en `.env.multihost` — gitignored, no commitear.
- TLS nginx es autofirmado (`https://localhost`) — el navegador chillará la primera vez, aceptar.
- `AUTH_MODE=mock`, `KMS_MODE=mock`, `STORAGE_ENCRYPTION=none`. Para el piloto interno es suficiente; el upgrade a Keycloak/Vault/SSE-C vive en el plan v0.3 (arquitectura hospitalaria completa).

## Backup mínimo para el piloto

```powershell
# Dump manual — cópialo a tu OneDrive / NAS personal si el piloto importa
docker compose -f infra\compose\docker-compose.multihost.yml --env-file infra\compose\.env.multihost exec postgres `
    pg_dump -U vcapp vcapp > backups\vcapp-$(Get-Date -Format yyyyMMdd-HHmmss).sql
```

MinIO: Spark ya persiste en volumen; si ese host vuela, pierdes las referencias y síntesis. Asumido para el piloto.
