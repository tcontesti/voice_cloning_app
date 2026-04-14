"""Per-job progress events via Redis pub/sub.

Channel layout: `progress:job:<job_id>` (string job UUID).
Worker publishes; FastAPI WebSocket subscribes and forwards as JSON frames.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

import redis

from app.core.config import get_settings


def _channel(job_id: UUID | str) -> str:
    return f"progress:job:{job_id}"


@dataclass(frozen=True)
class ProgressEvent:
    job_id: str
    stage: str          # queued | loading_model | synthesizing | postproc | uploading | done | failed
    pct: int            # 0..100 monotonically increasing within a job
    message: str = ""
    payload: dict[str, Any] | None = None
    ts: float = 0.0


def _client() -> redis.Redis:
    s = get_settings()
    return redis.Redis(
        host=s.redis_host, port=s.redis_port, password=s.redis_password,
        decode_responses=True,
    )


def publish(event: ProgressEvent) -> None:
    body = asdict(event)
    if not body["ts"]:
        body["ts"] = time.time()
    _client().publish(_channel(event.job_id), json.dumps(body))


def emit(job_id: UUID | str, stage: str, pct: int, message: str = "", **payload: Any) -> None:
    publish(ProgressEvent(
        job_id=str(job_id), stage=stage, pct=pct, message=message,
        payload=payload or None,
    ))
