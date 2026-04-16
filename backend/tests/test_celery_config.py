"""Guardrails on Celery worker configuration.

A stuck task (CUDA deadlock, adapter infinite retry, dead broker on the
Spark side) used to park a worker forever because no time limit was
set. We now bound every task; the test locks that in so nobody drops
the limits later.
"""

from __future__ import annotations

from app.workers.celery_app import celery_app


def test_time_limits_are_configured() -> None:
    conf = celery_app.conf
    assert conf.task_soft_time_limit is not None, "soft time limit must be set"
    assert conf.task_time_limit is not None, "hard time limit must be set"
    # Hard limit has to be strictly greater so the soft handler has time
    # to flip the row to `failed` before SIGKILL.
    assert conf.task_time_limit > conf.task_soft_time_limit


def test_acks_late_survives_worker_crash() -> None:
    """Without task_acks_late, a worker killed mid-task silently drops
    the message. Combined with task_reject_on_worker_lost=True this is
    how jobs resume after the Spark reboots."""
    conf = celery_app.conf
    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True


def test_one_job_per_worker() -> None:
    """Prefetch > 1 would queue up TTS jobs in memory on a worker,
    defeating the point of per-queue GPU isolation."""
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_known_queues_are_registered() -> None:
    names = {q.name for q in celery_app.conf.task_queues or ()}
    assert {"synth.chatterbox", "synth.omnivoice", "synth.qwen3tts"} <= names
