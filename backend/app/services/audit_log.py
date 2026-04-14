"""Append-only audit log service.

Insertion is serialized via row-level lock on the previous tail row (or table
advisory lock for the first insert) so concurrent writers can't race on
prev_hash. We use Postgres advisory lock keyed to the audit table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import GENESIS_PREV_HASH, compute_entry_hash
from app.db.models.audit import AuditLog

# Constant key for the audit-write advisory lock. Any positive int works.
_AUDIT_LOCK_KEY = 919191


async def append(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Append one entry. Caller owns the transaction (commit/rollback)."""
    payload = payload or {}

    # Serialize against concurrent inserts so prev_hash stays consistent.
    await session.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=_AUDIT_LOCK_KEY))

    tail = await session.scalar(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    )
    prev_hash = tail.hash if tail is not None else GENESIS_PREV_HASH

    now = datetime.now(timezone.utc)
    h = compute_entry_hash(
        prev_hash=prev_hash,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        created_at=now,
    )
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        prev_hash=prev_hash,
        hash=h,
        created_at=now,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_all(session: AsyncSession) -> list[AuditLog]:
    res = await session.scalars(select(AuditLog).order_by(AuditLog.id.asc()))
    return list(res.all())
