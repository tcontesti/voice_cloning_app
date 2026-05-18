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

Desde el navegador en `http://localhost:5173` → login con `paciente@example.local / <password seed>`, sube una referencia, genera una síntesis. Si llega a `done` con el watermark verificado, el flujo extremo-a-extremo funciona.

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
   típicamente `SPARK_HOST.tail-xxxxx.ts.net`.
5. Editar `~/.ssh/config` en Windows:
   ```
   Host spark
       Hostname SPARK_HOST.tail-xxxxx.ts.net
       # o: Hostname 100.x.x.x
       User SPARK_USER
       IdentityFile ~/.ssh/id_ed25519
   ```

Beneficio: SSH (y por tanto el túnel autossh) sigue funcionando sin tocar
nada cuando la Spark cambia de red o despierta. Tailscale atraviesa NAT
vía DERP.

No hay integración en el código — Tailscale es una capa de red, no una
dependencia de la app.

### Watchdog del túnel (Task Scheduler de Windows)

`scripts\tunnel_watchdog.ps1` se registra como tarea programada **"VCApp
Tunnel Watchdog"** que se ejecuta cada minuto en la cuenta del usuario (sin
admin). En cada tick:

1. Si **no** existe el flag `%LOCALAPPDATA%\vcapp\tunnel_enabled.flag` → el
   watchdog sale silenciosamente (es un no-op). Así `dev_stop.ps1` puede
   pausarlo borrando solo el flag, sin desregistrar la tarea.
2. Si `autossh.exe` corre **y** `localhost:5682` (forward de RabbitMQ AMQP)
   responde a TCP → tunnel sano, no hace nada. La existencia del proceso no
   basta: autossh en Windows puede quedarse zombie (proceso vivo sin hijo
   ssh y sin puerto abierto), por eso se prueba el puerto.
3. Si `autossh.exe` corre pero el puerto está muerto **más allá** de un
   periodo de gracia de 30s (para no matar a autossh durante el handshake
   inicial cuando Spark es brevemente inalcanzable) → mata el zombie
   (`autossh.exe` + cualquier `ssh.exe` huérfano que retenga los puertos
   forwardeados a `spark`) y cae al paso 4.
4. Si `autossh.exe` no está → lee el flag (JSON con `SparkAlias`,
   `AutosshPath`, `SshPath` capturados al arrancar) y relanza autossh con los
   mismos `-L`/`-R` que `dev_start.ps1`. Detección de la caída ≤60s,
   recuperación visible en la UI ≤90s.

`dev_start.ps1` automatiza todo el ciclo cuando hay autossh disponible:

- crea `%LOCALAPPDATA%\vcapp\tunnel_enabled.flag` con el JSON de contexto,
- llama a `install_watchdog.ps1` (idempotente: hace
  unregister-then-register, así la tarea siempre refleja el script actual).

`dev_stop.ps1` borra el flag **antes** de matar los procesos para evitar que
un tick concurrente del watchdog resucite autossh durante el teardown.

Logs: `%LOCALAPPDATA%\vcapp\logs\tunnel_watchdog.log`. Solo se escriben
cambios de estado (respawn, zombie-kill, error). Un fichero vacío o sin
entradas recientes significa que autossh ha estado sano todo el tiempo. Para
verificar que la tarea está corriendo aunque no haya escrito nada:

```powershell
Get-ScheduledTaskInfo -TaskName "VCApp Tunnel Watchdog"   # mira LastRunTime
```

Si el camino degradado (`-UseSSH` o autossh no instalado) está activo, el
watchdog **no** se registra: `ssh` plano no tiene semántica de respawn y el
flag nunca se crea.

Desinstalación:

```powershell
.\scripts\uninstall_watchdog.ps1
```

Esto desregistra `"VCApp Tunnel Watchdog"`, limpia la antigua tarea
`"VoiceCloningDevStart"` (versión anterior, lanzaba dev_start al login)
si todavía existe, y borra el flag.

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

### Dependencia crítica del reverse-tunnel Redis (puerto 6380)

Los workers Celery en la Spark usan como **result backend** el Redis que corre
en el PC, alcanzado a través del reverse tunnel `-R 6380:localhost:6379`. Esto
tiene una implicación operativa que no es obvia:

- **Si el reverse `-R 6380` no se establece, los workers consumen el mensaje
  de RabbitMQ pero no pueden persistir el resultado de la task.** La fila
  `app.syntheses` queda en `queued` para siempre desde el punto de vista de
  la UI, aunque el audio sí se genere y quede en MinIO.
- Síntoma observable: `docker exec vcapp-multihost-backend-1 journalctl …` del
  worker (o `ssh spark "journalctl --user -u worker_chatterbox -n 50"`) muestra
  `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6380.
  Connection refused.`
- El túnel puede fallar al *reestablecerse* (no al arrancar) cuando una sesión
  ssh previa dejó el puerto 5433 o 6380 bound en la Spark; sin
  `ExitOnForwardFailure=yes` la sesión ssh sigue viva pero los `-R` no
  re-bindan. Confirmarlo con `ssh spark "ss -tln | grep -E ':(5433|6380)'"`
  desde otra shell — si los puertos aparecen listados pero `Invoke-RestMethod
  http://localhost:8000/system/health` devuelve workers `offline` en un job
  real, los binds son de una sesión huérfana.
- Recuperación: `ssh spark "fuser -n tcp 5433 6380"`, matar esos sshd
  huérfanos, y relanzar el túnel (`.\scripts\dev_stop.ps1` + `dev_start.ps1`).
  El `ClientAliveInterval 30` recomendado en el sshd de la Spark reduce la
  ventana en la que esto puede pasar.
- Alternativa de diseño (no implementada): mover el result backend a un Redis
  local de la Spark. Elimina esta dependencia pero la API en el PC pierde
  visibilidad de estados intermedios más allá de lo que emite el pub/sub.
  Evaluación técnica en `SUMMARY_pc_medium.md`.
