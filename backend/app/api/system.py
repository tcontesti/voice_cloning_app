"""System health endpoint.

Aggregates liveness of the components the UI needs to know about so it
can degrade gracefully when the Spark tunnel is down:
  - postgres (always local to the API pod)
  - redis    (local)
  - rabbitmq (on Spark — tunneled)
  - minio    (on Spark — tunneled)
  - workers  (per Celery queue, via `inspect.ping`)

Every probe runs with a short timeout; the whole response is cached for
5 s so the UI can poll every 10 s without hammering any service. No Redis
cache on purpose — this endpoint must answer even when Redis is down.
"""

from __future__ import annotations

import asyncio
import socket
import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine as async_engine

router = APIRouter(prefix="/system", tags=["system"])

Status = Literal["ok", "unreachable"]
WorkerStatus = Literal["available", "offline"]

# Queue names must stay in sync with app/workers/celery_app.py task_routes.
KNOWN_WORKERS: tuple[str, ...] = ("chatterbox", "omnivoice", "qwen3tts", "elevenlabs")

_PROBE_TIMEOUT_S = 2.0
# Celery `inspect.active_queues` over the SSH tunnel takes ~3s round trip
# to broadcast + collect replies. The TCP probes still use the short
# timeout; only the worker probe gets the longer leash.
_WORKER_PROBE_TIMEOUT_S = 5.0
_CACHE_TTL_S = 5.0


class SystemHealth(BaseModel):
    backend: Literal["ok"] = "ok"
    postgres: Status
    redis: Status
    rabbitmq: Status
    minio: Status
    workers: dict[str, WorkerStatus]
    spark_reachable: bool


_cache: dict[str, tuple[float, SystemHealth]] = {}


async def _probe_tcp(host: str, port: int) -> Status:
    """TCP connect in a worker thread so the event loop stays free."""
    def _connect() -> bool:
        try:
            with socket.create_connection((host, port), timeout=_PROBE_TIMEOUT_S):
                return True
        except OSError:
            return False

    try:
        ok = await asyncio.wait_for(asyncio.to_thread(_connect), timeout=_PROBE_TIMEOUT_S + 0.5)
    except asyncio.TimeoutError:
        return "unreachable"
    return "ok" if ok else "unreachable"


async def _probe_postgres() -> Status:
    try:
        async with async_engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=_PROBE_TIMEOUT_S)
        return "ok"
    except Exception:
        return "unreachable"


async def _probe_workers() -> dict[str, WorkerStatus]:
    """Call celery `inspect.active_queues` in a thread and map queues → status.

    We treat a worker as available iff at least one running worker is consuming
    its queue. `inspect.ping` alone doesn't tell us which queues a replier
    serves, so `active_queues` is the honest check.
    """
    def _inspect() -> dict[str, WorkerStatus]:
        # Imported lazily so the API boots even if Celery/Kombu have an issue.
        from app.workers.celery_app import celery_app

        result: dict[str, WorkerStatus] = {w: "offline" for w in KNOWN_WORKERS}
        try:
            insp = celery_app.control.inspect(timeout=_WORKER_PROBE_TIMEOUT_S)
            queues_by_worker = insp.active_queues() or {}
        except Exception:
            return result

        consumed: set[str] = set()
        for entries in queues_by_worker.values():
            for q in entries or []:
                name = q.get("name", "")
                consumed.add(name)

        for name in KNOWN_WORKERS:
            if f"synth.{name}" in consumed:
                result[name] = "available"
        return result

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_inspect),
            timeout=_WORKER_PROBE_TIMEOUT_S + 1.5,
        )
    except asyncio.TimeoutError:
        return {w: "offline" for w in KNOWN_WORKERS}


async def _compute_health() -> SystemHealth:
    s = get_settings()
    postgres, redis, rabbit, minio, workers = await asyncio.gather(
        _probe_postgres(),
        _probe_tcp(s.redis_host, s.redis_port),
        _probe_tcp(s.rabbitmq_host, s.rabbitmq_port),
        _probe_tcp(s.minio_host, s.minio_port),
        _probe_workers(),
    )
    spark_reachable = rabbit == "ok" and minio == "ok"
    return SystemHealth(
        postgres=postgres,
        redis=redis,
        rabbitmq=rabbit,
        minio=minio,
        workers=workers,
        spark_reachable=spark_reachable,
    )


@router.get("/health", response_model=SystemHealth)
async def system_health() -> SystemHealth:
    now = time.monotonic()
    cached = _cache.get("health")
    if cached and (now - cached[0]) < _CACHE_TTL_S:
        return cached[1]
    value = await _compute_health()
    _cache["health"] = (now, value)
    return value


def _reset_cache_for_tests() -> None:
    """Hook used by pytest to force a fresh probe."""
    _cache.clear()
