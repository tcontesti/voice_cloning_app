"""Celery app for synthesis workers.

The worker process runs natively on the Spark using its venv with torch+TTS.
This module is imported both by the worker (`celery -A app.workers.celery_app`)
and by the FastAPI API (which uses `celery_app.send_task`) — keep deps light.

Queue topology — one queue per model so we can run dedicated worker processes
that own their VRAM and don't interleave models on the same GPU stream:
    synth.chatterbox  → worker_chatterbox.service
    synth.omnivoice   → worker_omnivoice.service   (M6)
    synth.qwen3tts    → worker_qwen3.service       (M7, isolated venv)
"""

from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import get_settings

_s = get_settings()
_BROKER = (
    f"amqp://{_s.rabbitmq_user}:{_s.rabbitmq_password}"
    f"@{_s.rabbitmq_host}:{_s.rabbitmq_port}//"
)
_BACKEND = f"redis://:{_s.redis_password}@{_s.redis_host}:{_s.redis_port}/1"

celery_app = Celery(
    "vcapp",
    broker=_BROKER,
    backend=_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,    # one job at a time per worker — TTS is heavy
    worker_max_tasks_per_child=50,   # periodic recycling against memory drift
    # Bound every task. Without these a CUDA deadlock or an adapter hang
    # would park the worker for the UI's whole session. Soft limit raises
    # SoftTimeLimitExceeded so the task gets a chance to clean up and mark
    # the row `failed`; hard limit kills the worker process as a last
    # resort. Numbers sized to the slowest model (qwen3tts) + headroom.
    task_soft_time_limit=600,   # 10 min
    task_time_limit=900,        # 15 min
    task_default_queue="synth.chatterbox",
    task_default_exchange="synth",
    task_default_routing_key="synth.chatterbox",
    task_queues=(
        Queue("synth.chatterbox", Exchange("synth", type="direct"), routing_key="synth.chatterbox"),
        Queue("synth.omnivoice",  Exchange("synth", type="direct"), routing_key="synth.omnivoice"),
        Queue("synth.qwen3tts",   Exchange("synth", type="direct"), routing_key="synth.qwen3tts"),
        Queue("synth.elevenlabs", Exchange("synth", type="direct"), routing_key="synth.elevenlabs"),
    ),
    # Callers always pass queue=synth.<model> explicitly in send_task(...),
    # so no task_routes map is needed. Celery 5.6 rejects lambda-valued
    # task_routes entries with `TypeError: 'function' object is not iterable`.
)
