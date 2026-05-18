#!/usr/bin/env bash
# Launch one Celery worker bound to a single model queue.
# Usage:
#   bash worker/start_worker.sh chatterbox
set -euo pipefail

MODEL="${1:?usage: start_worker.sh <chatterbox|omnivoice|qwen3tts>}"
VENV="${VC_VENV:-$HOME/voice_cloning_env/.venv}"
APP_ROOT="${VC_APP_ROOT:-$HOME/voice_cloning_app}"
SCRIPTS_DIR="${VC_SCRIPTS_DIR:-$HOME/voice_cloning/scripts}"

# Env source precedence:
#   1. $VC_WORKER_ENV (explicit override)
#   2. ~/.config/vcapp/worker.env  (dev multi-host default — localhost hosts)
#   3. $APP_ROOT/.env              (Docker-network hostnames; overrides below patch them)
WORKER_ENV="${VC_WORKER_ENV:-$HOME/.config/vcapp/worker.env}"
if [[ -f "$WORKER_ENV" ]]; then
    set -a
    # shellcheck disable=SC1090,SC1091
    . "$WORKER_ENV"
    set +a
elif [[ -f "$APP_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1090,SC1091
    . "$APP_ROOT/.env"
    set +a
fi

# Backend code is on PYTHONPATH; we don't pip-install it into the venv.
export PYTHONPATH="$APP_ROOT/backend:${PYTHONPATH:-}"
export VC_SCRIPTS_DIR="$SCRIPTS_DIR"

# Native-on-Spark override: the sourced .env uses Docker-internal hostnames
# (rabbitmq, redis, minio, postgres) that only resolve inside the compose
# network. Workers run outside Docker, so point them at the host's loopback
# where the compose stack publishes its ports. Override per-var if needed
# (e.g. for DB on another host) by exporting before invoking this script.
export RABBITMQ_HOST="${RABBITMQ_HOST_OVERRIDE:-localhost}"
export REDIS_HOST="${REDIS_HOST_OVERRIDE:-localhost}"
export MINIO_HOST="${MINIO_HOST_OVERRIDE:-localhost}"
export POSTGRES_HOST="${POSTGRES_HOST_OVERRIDE:-localhost}"
exec "$VENV/bin/celery" -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --queues="synth.${MODEL}" \
    --hostname="worker-${MODEL}@%h"
