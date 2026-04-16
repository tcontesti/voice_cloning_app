"""Celery tasks. Worker-side imports happen lazily inside the task body so
the FastAPI side that also imports `celery_app` doesn't pull torch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from celery import shared_task
from celery.exceptions import Ignore
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.workers.celery_app import celery_app  # noqa: F401  (registers app)
from app.workers.progress import emit

log = structlog.get_logger(__name__)

# Sync engine for the worker — Celery doesn't need async; keep imports light.
_sync_engine = None
_SyncSession: sessionmaker | None = None


def _session_factory() -> sessionmaker:
    global _sync_engine, _SyncSession
    if _SyncSession is not None:
        return _SyncSession
    from sqlalchemy import create_engine

    s = get_settings()
    url = (
        f"postgresql+psycopg2://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{s.postgres_db}"
    )
    _sync_engine = create_engine(url, pool_pre_ping=True, future=True)
    _SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _SyncSession


def _fetch_reference_wav(s3_key: str) -> bytes:
    from app.services import storage
    return storage.get_object(bucket=get_settings().minio_bucket_recordings, key=s3_key)


def _persist_reference_to_disk(raw: bytes) -> str:
    from pathlib import Path
    p = Path(f"/tmp/vcref-{uuid4().hex}.wav")
    p.write_bytes(raw)
    return str(p)


@shared_task(bind=True, name="app.workers.tasks.synthesize")
def synthesize(self, *, synthesis_id: str, model: str) -> dict:
    """Run one synthesis job end-to-end and update DB.

    Side effects: writes WAV to MinIO, updates row status, audits, publishes
    progress events on Redis pub/sub channel `progress:job:<synthesis_id>`.
    """
    from app.db.models.recording import Recording
    from app.db.models.synthesis import Synthesis, SynthesisStatus
    from app.db.models.voice_profile import VoiceProfile
    from app.services import audit_log as audit_svc
    from app.services import storage
    from app.workers.adapters import get_adapter  # noqa: F401  (warmup)
    from app.workers.postproc import aasist as aasist_mod
    from app.workers.postproc import normalize as norm
    from app.workers.postproc import watermark as wm
    from app.workers.registry import registry

    job = synthesis_id
    SessionFn = _session_factory()
    db: Session = SessionFn()
    # Tracks on-disk reference WAV so we can unlink it in `finally`, even when
    # the adapter crashes mid-synthesis — otherwise /tmp/vcref-*.wav piles up.
    ref_path: str | None = None
    try:
        emit(job, "queued", 5, "preparando")
        syn = db.get(Synthesis, UUID(synthesis_id))
        if syn is None:
            raise Ignore()

        syn.status = SynthesisStatus.running
        syn.started_at = datetime.now(timezone.utc)
        db.commit()

        profile = db.get(VoiceProfile, syn.profile_id)
        if profile is None or not profile.reference_ids:
            raise RuntimeError("voice profile has no reference recordings")
        ref = db.scalar(
            select(Recording).where(
                Recording.id == profile.reference_ids[0],
                Recording.deleted_at.is_(None),
            )
        )
        if ref is None:
            raise RuntimeError("reference recording missing or deleted")

        emit(job, "loading_model", 15, f"cargando {model}")
        adapter = registry.get(model)

        emit(job, "synthesizing", 35, "sintetizando")
        ref_bytes = _fetch_reference_wav(ref.s3_key)
        ref_path = _persist_reference_to_disk(ref_bytes)
        out = adapter.synthesize(text=syn.text, reference_wav=ref_path, options=dict(syn.options))

        scheme, must_apply = wm.scheme_for_model(model)
        samples = out.samples
        sr = out.sample_rate
        if must_apply:
            emit(job, "postproc", 55, f"aplicando watermark ({scheme})")
            samples, sr = wm.apply_audioseal(samples, sr)

        emit(job, "postproc", 65, "verificando watermark")
        wm_result = wm.verify(scheme, samples, sr)

        emit(job, "postproc", 75, "anti-spoofing")
        try:
            aasist_score = aasist_mod.score(samples, sr)
        except Exception as e:
            log.warning("aasist.failed", error=str(e))
            aasist_score = None

        emit(job, "uploading", 90, "guardando audio")
        wav_bytes, target_sr, duration_s = norm.to_wav_bytes(samples, sr)
        s3_key = f"users/{syn.user_id}/syntheses/{syn.id.hex}.wav"
        storage.put_object(
            bucket=get_settings().minio_bucket_syntheses,
            key=s3_key,
            data=wav_bytes,
            content_type="audio/wav",
        )

        rtf = out.gen_time_s / max(duration_s, 1e-6)
        syn.s3_key_output = s3_key
        syn.duration_s = duration_s
        syn.rtf = rtf
        syn.watermark_scheme = wm_result.scheme
        syn.watermark_verified = wm_result.detected
        syn.aasist_score = aasist_score
        syn.status = SynthesisStatus.succeeded
        syn.completed_at = datetime.now(timezone.utc)

        # Audit append has to land atomically with the status flip. A prior
        # split-transaction layout (status commit → audit commit) left the
        # audit row missing if the worker crashed between them, breaking the
        # hash chain's invariant that every state change is recorded.
        audit_payload = {
            "model": model,
            "duration_s": round(duration_s, 3),
            "rtf": round(rtf, 3),
            "watermark_scheme": wm_result.scheme,
            "watermark_verified": wm_result.detected,
            "aasist_score": round(aasist_score, 4) if aasist_score is not None else None,
        }
        _audit_sync(db, actor_id=syn.user_id, action="synthesis.succeeded",
                    resource_type="synthesis", resource_id=str(syn.id), payload=audit_payload)
        db.commit()

        # Hard policy: missing watermark on a model that is supposed to embed
        # one means the pipeline lost it (or model swap upstream) — alert.
        if not wm_result.detected:
            log.error("watermark.missing", synthesis_id=str(syn.id), scheme=wm_result.scheme)

        emit(job, "done", 100, "completado",
             watermark_verified=wm_result.detected, aasist_score=aasist_score)
        return {
            "synthesis_id": str(syn.id),
            "s3_key": s3_key,
            "duration_s": duration_s,
            "rtf": rtf,
            "watermark_verified": wm_result.detected,
            "aasist_score": aasist_score,
        }

    except Exception as e:
        log.exception("synthesis.failed", synthesis_id=synthesis_id)
        try:
            syn = db.get(Synthesis, UUID(synthesis_id))
            if syn is not None:
                syn.status = SynthesisStatus.failed
                syn.error = str(e)[:1000]
                syn.completed_at = datetime.now(timezone.utc)
                db.commit()
                _audit_sync(db, actor_id=syn.user_id, action="synthesis.failed",
                            resource_type="synthesis", resource_id=str(syn.id),
                            payload={"error": str(e)[:500]})
                db.commit()
        except Exception:
            log.exception("synthesis.fail_persist_failed")
        emit(synthesis_id, "failed", 100, str(e))
        raise
    finally:
        if ref_path is not None:
            try:
                from pathlib import Path
                Path(ref_path).unlink(missing_ok=True)
            except Exception:
                log.warning("reference.tempfile_cleanup_failed", path=ref_path, exc_info=True)
        db.close()


def _audit_sync(db: Session, *, actor_id, action, resource_type, resource_id, payload) -> None:
    """Sync version of audit append (the async service uses asyncpg).

    Mirrors `app.services.audit_log.append` but on a sync session — same
    canonical hash, same advisory lock semantics.
    """
    import hashlib
    import json

    from sqlalchemy import text

    from app.core.audit import GENESIS_PREV_HASH, compute_entry_hash
    from app.db.models.audit import AuditLog

    db.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=919191))
    tail = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev_hash = tail.hash if tail is not None else GENESIS_PREV_HASH
    now = datetime.now(timezone.utc)
    h = compute_entry_hash(
        prev_hash=prev_hash, actor_id=actor_id, action=action,
        resource_type=resource_type, resource_id=resource_id,
        payload=payload, created_at=now,
    )
    db.add(AuditLog(
        actor_id=actor_id, action=action, resource_type=resource_type,
        resource_id=resource_id, payload=payload,
        prev_hash=prev_hash, hash=h, created_at=now,
    ))
    db.flush()
    # silence unused-import warning when not consuming hashlib/json
    _ = hashlib, json
