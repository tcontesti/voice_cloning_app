"""Recording service — orchestrates validate → store → persist → audit."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.recording import Recording
from app.db.models.user import User
from app.services import audio_validation as av
from app.services import audit_log as audit_svc
from app.services import storage


def _build_s3_key(user_id: UUID) -> str:
    # Stable, opaque, no PII. user-prefixed for prod IAM scoping in M8.
    return f"users/{user_id}/refs/{uuid4().hex}.wav"


async def upload(
    session: AsyncSession,
    *,
    user: User,
    raw_bytes: bytes,
    content_type: str,
    ip: str | None,
) -> Recording:
    metrics = av.analyze(raw_bytes)
    av.assert_acceptable(metrics)

    sha = hashlib.sha256(raw_bytes).hexdigest()

    # Reject duplicate (same user re-uploading same bytes).
    existing = await session.scalar(
        select(Recording).where(
            Recording.user_id == user.id,
            Recording.sha256 == sha,
            Recording.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return existing

    s3_key = _build_s3_key(user.id)
    bucket = get_settings().minio_bucket_recordings
    storage.put_object(bucket=bucket, key=s3_key, data=raw_bytes, content_type=content_type)

    rec = Recording(
        user_id=user.id,
        s3_key=s3_key,
        duration_s=metrics.duration_s,
        sample_rate=metrics.sample_rate,
        channels=metrics.channels,
        snr_db=metrics.snr_db,
        lufs=metrics.lufs,
        speech_ratio=metrics.speech_ratio,
        sha256=sha,
    )
    session.add(rec)
    await session.flush()

    await audit_svc.append(
        session,
        actor_id=user.id,
        action="recording.uploaded",
        resource_type="recording",
        resource_id=str(rec.id),
        payload={
            "duration_s": round(metrics.duration_s, 3),
            "sample_rate": metrics.sample_rate,
            "snr_db": round(metrics.snr_db, 1) if metrics.snr_db is not None else None,
            "speech_ratio": round(metrics.speech_ratio, 3),
            "sha256": sha,
            "ip": ip,
        },
    )
    return rec


async def list_for_user(session: AsyncSession, *, user_id: UUID) -> list[Recording]:
    rows = await session.scalars(
        select(Recording)
        .where(Recording.user_id == user_id, Recording.deleted_at.is_(None))
        .order_by(Recording.created_at.desc())
    )
    return list(rows.all())


async def get_owned(
    session: AsyncSession, *, user_id: UUID, recording_id: UUID
) -> Recording | None:
    rec = await session.get(Recording, recording_id)
    if rec is None or rec.user_id != user_id or rec.deleted_at is not None:
        return None
    return rec


async def soft_delete(
    session: AsyncSession, *, user: User, recording_id: UUID, ip: str | None
) -> Recording | None:
    rec = await get_owned(session, user_id=user.id, recording_id=recording_id)
    if rec is None:
        return None
    rec.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    await audit_svc.append(
        session,
        actor_id=user.id,
        action="recording.soft_deleted",
        resource_type="recording",
        resource_id=str(rec.id),
        payload={"ip": ip},
    )
    return rec
