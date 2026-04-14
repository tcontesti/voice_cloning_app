from typing import Annotated

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


@router.get("/logs", response_model=AuditPage)
async def list_logs(
    _: AdminOrAuditor,
    session: SessionDep,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AuditPage:
    total = await session.scalar(select(func.count()).select_from(AuditLog)) or 0
    rows = (
        await session.scalars(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
        )
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
