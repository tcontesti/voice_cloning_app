from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import SessionDep, require_roles
from app.core.audit import verify_chain
from app.db.models.audit import AuditLog
from app.db.models.user import UserRole

router = APIRouter(prefix="/audit", tags=["audit"])

AdminOrAuditor = Annotated[
    object, Depends(require_roles(UserRole.admin, UserRole.auditor))
]


class AuditEntryOut(BaseModel):
    id: int
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    payload: dict[str, Any]
    prev_hash: str
    hash: str
    created_at: str

    @classmethod
    def from_row(cls, r: AuditLog) -> "AuditEntryOut":
        return cls(
            id=r.id,
            actor_id=str(r.actor_id) if r.actor_id else None,
            action=r.action,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            payload=r.payload or {},
            prev_hash=r.prev_hash,
            hash=r.hash,
            created_at=r.created_at.isoformat(),
        )


class AuditPage(BaseModel):
    items: list[AuditEntryOut]
    total: int
    limit: int
    offset: int


class ChainStatus(BaseModel):
    ok: bool
    broken_at: int | None
    total_entries: int


class AuditStats(BaseModel):
    total: int
    by_action: dict[str, int]
    by_resource: dict[str, int]
    first_ts: str | None
    last_ts: str | None


@router.get("/logs", response_model=AuditPage)
async def list_logs(
    _: AdminOrAuditor,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None, description="exact action match, e.g. 'auth.login.ok'"),
    action_prefix: str | None = Query(None, description="prefix match, e.g. 'synthesis.'"),
    actor_id: UUID | None = None,
    resource_type: str | None = None,
    since: datetime | None = Query(None, description="ISO datetime, inclusive"),
    until: datetime | None = Query(None, description="ISO datetime, exclusive"),
) -> AuditPage:
    q = select(AuditLog)
    count_q = select(func.count()).select_from(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if action_prefix:
        q = q.where(AuditLog.action.like(f"{action_prefix}%"))
        count_q = count_q.where(AuditLog.action.like(f"{action_prefix}%"))
    if actor_id is not None:
        q = q.where(AuditLog.actor_id == actor_id)
        count_q = count_q.where(AuditLog.actor_id == actor_id)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
        count_q = count_q.where(AuditLog.resource_type == resource_type)
    if since is not None:
        q = q.where(AuditLog.created_at >= since)
        count_q = count_q.where(AuditLog.created_at >= since)
    if until is not None:
        q = q.where(AuditLog.created_at < until)
        count_q = count_q.where(AuditLog.created_at < until)

    total = await session.scalar(count_q) or 0
    rows = (
        await session.scalars(q.order_by(AuditLog.id.desc()).limit(limit).offset(offset))
    ).all()
    return AuditPage(
        items=[AuditEntryOut.from_row(r) for r in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get("/verify", response_model=ChainStatus)
async def verify(_: AdminOrAuditor, session: SessionDep) -> ChainStatus:
    rows = (await session.scalars(select(AuditLog).order_by(AuditLog.id.asc()))).all()
    ok, broken = verify_chain(list(rows))
    return ChainStatus(ok=ok, broken_at=broken, total_entries=len(rows))


@router.get("/stats", response_model=AuditStats)
async def stats(_: AdminOrAuditor, session: SessionDep) -> AuditStats:
    total = int(await session.scalar(select(func.count()).select_from(AuditLog)) or 0)
    by_action_rows = (
        await session.execute(
            select(AuditLog.action, func.count()).group_by(AuditLog.action)
        )
    ).all()
    by_resource_rows = (
        await session.execute(
            select(AuditLog.resource_type, func.count()).group_by(AuditLog.resource_type)
        )
    ).all()
    first_ts = await session.scalar(select(func.min(AuditLog.created_at)))
    last_ts = await session.scalar(select(func.max(AuditLog.created_at)))
    return AuditStats(
        total=total,
        by_action={str(a): int(c) for a, c in by_action_rows},
        by_resource={str(a): int(c) for a, c in by_resource_rows},
        first_ts=first_ts.isoformat() if first_ts else None,
        last_ts=last_ts.isoformat() if last_ts else None,
    )
