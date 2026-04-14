#!/usr/bin/env bash
# Launch one Celery worker bound to a single model queue.
# Usage:
#   bash worker/start_worker.sh chatterbox
set -euo pipefail

MODEL="${1:?usage: start_worker.sh <chatterbox|omnivoice|qwen3tts>}"
VENV="${VC_VENV:-$HOME/voice_cloning_env/.venv}"
APP_ROOT="${VC_APP_ROOT:-$HOME/voice_cloning_app}"
SCRIPTS_DIR="${VC_SCRIPTS_DIR:-$HOME/voice_cloning/scripts}"

# .env must be present at the app root (or pass env vars directly).
if [[ -f "$APP_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1090,SC1091
    . "$APP_ROOT/.env"
    set +a
fi

# Backend code is on PYTHONPATH; we don't pip-install it into the venv.
export PYTHONPATH="$APP_ROOT/backend:${PYTHONPATH:-}"
export VC_SCRIPTS_DIR="$SCRIPTS_DIR"

# Spark dev runs services on localhost; override RABBITMQ_HOST/REDIS_HOST/POSTGRES_HOST
# in the environment if running on a different host than the docker stack.
exec "$VENV/bin/celery" -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --queues="synth.${MODEL}" \
    --hostname="worker-${MODEL}@%h"
