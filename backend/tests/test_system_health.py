"""Tests for /system/health.

We monkeypatch the probe coroutines so the suite doesn't need a live
RabbitMQ / MinIO / Celery cluster. The endpoint itself + the cache are
exercised end-to-end.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import system
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    system._reset_cache_for_tests()


def _patch_probes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    postgres: str = "ok",
    redis: str = "ok",
    rabbit: str = "ok",
    minio: str = "ok",
    workers: dict[str, str] | None = None,
) -> None:
    if workers is None:
        workers = {w: "available" for w in system.KNOWN_WORKERS}

    async def _pg() -> str: return postgres

    async def _tcp(host: str, port: int) -> str:
        # Match the endpoint's call order: redis, rabbit, minio.
        s = system.get_settings()
        if (host, port) == (s.redis_host, s.redis_port): return redis
        if (host, port) == (s.rabbitmq_host, s.rabbitmq_port): return rabbit
        if (host, port) == (s.minio_host, s.minio_port): return minio
        return "unreachable"

    async def _wk() -> dict[str, str]:
        return dict(workers)

    monkeypatch.setattr(system, "_probe_postgres", _pg)
    monkeypatch.setattr(system, "_probe_tcp", _tcp)
    monkeypatch.setattr(system, "_probe_workers", _wk)


def test_all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_probes(monkeypatch)
    r = client.get("/system/health")
    assert r.status_code == 200
    body: dict[str, Any] = r.json()
    assert body["backend"] == "ok"
    assert body["postgres"] == "ok"
    assert body["redis"] == "ok"
    assert body["rabbitmq"] == "ok"
    assert body["minio"] == "ok"
    assert body["spark_reachable"] is True
    assert body["workers"]["chatterbox"] == "available"


def test_rabbitmq_down_marks_spark_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_probes(
        monkeypatch,
        rabbit="unreachable",
        workers={w: "offline" for w in system.KNOWN_WORKERS},
    )
    r = client.get("/system/health")
    body = r.json()
    assert body["rabbitmq"] == "unreachable"
    assert body["spark_reachable"] is False
    assert body["workers"]["chatterbox"] == "offline"


def test_everything_down_except_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_probes(
        monkeypatch,
        postgres="unreachable",
        redis="unreachable",
        rabbit="unreachable",
        minio="unreachable",
        workers={w: "offline" for w in system.KNOWN_WORKERS},
    )
    r = client.get("/system/health")
    body = r.json()
    assert body["backend"] == "ok"   # endpoint is answering
    assert body["postgres"] == "unreachable"
    assert body["spark_reachable"] is False
    assert all(s == "offline" for s in body["workers"].values())


def test_partial_workers_online(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_probes(
        monkeypatch,
        workers={
            "chatterbox": "available",
            "omnivoice": "offline",
            "qwen3tts": "offline",
            "elevenlabs": "available",
        },
    )
    body = client.get("/system/health").json()
    assert body["spark_reachable"] is True   # transports up
    assert body["workers"]["chatterbox"] == "available"
    assert body["workers"]["omnivoice"] == "offline"


def test_response_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"pg": 0}

    async def _pg() -> str:
        calls["pg"] += 1
        return "ok"

    async def _tcp(host: str, port: int) -> str: return "ok"
    async def _wk() -> dict[str, str]:
        return {w: "available" for w in system.KNOWN_WORKERS}

    monkeypatch.setattr(system, "_probe_postgres", _pg)
    monkeypatch.setattr(system, "_probe_tcp", _tcp)
    monkeypatch.setattr(system, "_probe_workers", _wk)

    client.get("/system/health")
    client.get("/system/health")
    client.get("/system/health")
    assert calls["pg"] == 1   # subsequent calls served from the 5s cache
