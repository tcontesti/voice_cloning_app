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

## Gate VRAM relajado a 10 GB (solo dev multi-host)

En la Spark GB10 la memoria es **unificada** (121.7 GB total compartidos entre CPU y GPU). MedGemma 27B + DermApixel + otros ocupan ~69 GB de forma permanente, dejando típicamente **~30-50 GB libres**. El gate original de "40 GB libres" del plan v0.2 no aplica en este modo porque:

- Peak real con los 3 modelos simultáneamente cargados: Chatterbox 3.6 + OmniVoice 4 + Qwen3 5 = **~12.7 GB**.
- LRU residente (`UNLOAD_AFTER_S=600`) + Celery `prefetch=1` + 3 testers ⇒ concurrencia efectiva ~1-2 modelos a la vez, **<10 GB** en uso real.
- El gate estricto solo cobra sentido cuando hay despliegue hospitalario con carga concurrente real.

**Política dev multi-host:** mínimo **10 GB libres** antes de arrancar los 3 workers. Comprobar con:

```bash
source ~/voice_cloning_env/.venv/bin/activate
python -c "import torch; free,total=torch.cuda.mem_get_info(); print(f'{free/1024**3:.1f} GB libres / {total/1024**3:.1f} GB')"
```

Si <10 GB: arrancar solo Chatterbox (más liviano) y dejar Omni/Qwen3 hasta que se libere otra carga del sistema.

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

## Resiliencia — túnel que sobrevive al roaming de la Spark

La Spark viaja entre oficina y casa y se suspende de noche. Un `ssh -N` plano
muere en cuanto cambia la IP o la red; `autossh` lo resuelve reconectando
sólo.

### autossh (recomendado)

Instala uno de los dos en el PC Windows:

```powershell
# preferido — bucket main de scoop
scoop install autossh

# alternativa
winget install eternallybored.autossh
```

`scripts\dev_start.ps1` detecta autossh automáticamente y lo usa con
`AUTOSSH_GATETIME=0` (nunca se rinde) + keepalives cada 15s. Si autossh no
está instalado, el script cae a `ssh` plano con un aviso — sigue funcionando
pero tendrás que relanzar el túnel cada vez que la Spark se mueva.

Para forzar el camino `ssh` plano (debug):

```powershell
.\scripts\dev_start.ps1 -UseSSH
```

### Red estable con Tailscale

Aun con autossh, cambiar de red cambia la IP de la Spark y hay que actualizar
`~/.ssh/config`. Tailscale evita ese paso dándote una IP 100.x.x.x que viaja
con la máquina.

1. Instalar en el PC Windows: descargar desde `https://tailscale.com/download`
   (GUI) o `winget install tailscale.tailscale`.
2. Instalar en la Spark (Linux):
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
3. Loguear ambos con la **misma cuenta** Tailscale.
4. Obtener el hostname MagicDNS de la Spark (aparece en `tailscale status`),
   típicamente `spark-d03c.tail-xxxxx.ts.net`.
5. Editar `~/.ssh/config` en Windows:
   ```
   Host spark
       Hostname spark-d03c.tail-xxxxx.ts.net
       # o: Hostname 100.x.x.x
       User tonic
       IdentityFile ~/.ssh/id_ed25519
   ```

Beneficio: SSH (y por tanto el túnel autossh) sigue funcionando sin tocar
nada cuando la Spark cambia de red o despierta. Tailscale atraviesa NAT
vía DERP.

No hay integración en el código — Tailscale es una capa de red, no una
dependencia de la app.

### Watchdog opcional (Task Scheduler de Windows)

`scripts\install_watchdog.ps1` registra una tarea programada que lanza
`dev_start.ps1` al iniciar sesión. Off por defecto: activarla registra una
tarea en la cuenta del usuario sin pedir permiso cada vez que cambia de
rama, lo cual es mal patrón si varias personas clonan el repo.

Para activarla:

```powershell
.\scripts\install_watchdog.ps1
```

Para desinstalarla:

```powershell
.\scripts\uninstall_watchdog.ps1
```

### Modo degradado en la UI

El frontend polea `GET /system/health` cada 10s y muestra en la topbar un chip
con el estado agregado. Cuando la Spark está offline:

- El chip pasa a ámbar "SPARK OFFLINE".
- En `SynthesizeView`, las `ModelCard` de workers offline quedan deshabilitadas.
- El botón GENERATE se bloquea con tooltip *"Spark desconectada. Levántala e
  intenta de nuevo."*
- Si el job avanza y la Spark cae a mitad, `JobMonitor` detecta el stall
  (>30s sin progreso) y muestra un banner amber explicando que el mensaje
  sigue en RabbitMQ y se procesará cuando la Spark vuelva.

`RecordView` funciona igual — las grabaciones van al MinIO local del PC.
