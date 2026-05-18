# Voice cloning workers (Spark-native)

Workers run **natively** on the DGX Spark using the existing
`~/voice_cloning_env/.venv` (torch 2.11.0+cu130, chatterbox already installed).
They consume jobs from RabbitMQ (Docker stack on the Spark) and publish
progress to Redis pub/sub.

## One-time bootstrap

```bash
# 1) Add worker extras to the venv (idempotent, won't downgrade torch)
bash worker/install_into_venv.sh

# 2) Sanity check
~/voice_cloning_env/.venv/bin/python -c "import celery, torch, chatterbox; \
    print('celery', celery.__version__, '· torch', torch.__version__)"

# 3) Apply DB migration (in case backend was running an older schema)
make up                                              # ensure stack is up
docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.dev.yml \
    --env-file .env exec backend alembic upgrade head
```

## Run a worker

Foreground (debugging):
```bash
bash worker/start_worker.sh chatterbox
```

Background as systemd --user service (recommended):
```bash
mkdir -p ~/.config/systemd/user
cp worker/systemd/worker_chatterbox.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now worker_chatterbox
journalctl --user -u worker_chatterbox -f
```

## Why native, not Docker

- The TTS stack (chatterbox, torch cu130, _patches) is already installed in the
  venv and validated end-to-end in the original `voice_cloning` benchmark.
- Containerizing torch+CUDA on ARM64/GB10 doubles install/iteration time and
  loses access to the existing model checkpoints under `~/voice_cloning/models/`.
- VRAM bookkeeping (LRU unload, sharing with MedGemma+DermApixel) is easier
  with a single Python process per model.

## Topology

```
[FastAPI on Windows] ──HTTP──► [docker-compose on Spark]
                                 ├─ Postgres
                                 ├─ Redis  ◄── progress pub/sub ──► [Worker on Spark host]
                                 ├─ MinIO  ◄── ref WAVs / synth WAVs ─┘
                                 └─ RabbitMQ ◄── synth.chatterbox ────┘
```

In dev the Windows FastAPI reaches Spark via SSH tunnel:
```bash
ssh -L 5672:localhost:5672 -L 6379:localhost:6379 -L 9000:localhost:9000 \
    -L 5432:localhost:5432 SPARK_USER@SPARK_HOST
```

## Lazy-load LRU

Each worker process holds at most one model at a time. After 10 min idle the
model is unloaded to free VRAM (other tenants of the Spark: MedGemma 27B,
DermApixel). See `app/workers/registry.py`.

## Watermark + AASIST

- Chatterbox already embeds **PerTh** during synthesis. Worker only **verifies**
  via `resemble-perth` and stores `watermark_verified` in DB.
- AASIST anti-spoofing is run on every synthesis; score saved.

OmniVoice (M6) and Qwen3 (M7) will need AudioSeal applied post-hoc.
