"""Admin-only endpoints: user management and system stats."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import SessionDep, require_roles
from app.db.models.recording import Recording
from app.db.models.synthesis import Synthesis, SynthesisStatus
from app.db.models.user import User, UserRole
from app.db.models.voice_profile import VoiceProfile
from app.schemas.auth import CurrentUser
from app.services import audit_log as audit_svc

router = APIRouter(prefix="/admin", tags=["admin"])

AdminOnly = Annotated[User, Depends(require_roles(UserRole.admin))]


class UserListItem(BaseModel):
    id: UUID
    email: str
    role: UserRole
    full_name: str | None
    active: bool
    created_at: str


class UserList(BaseModel):
    items: list[UserListItem]
    total: int


class SetActiveIn(BaseModel):
    active: bool


class SystemStats(BaseModel):
    users_total: int
    users_active: int
    recordings_total: int
    recordings_active: int
    profiles_total: int
    syntheses_total: int
    syntheses_by_status: dict[str, int]


@router.get("/users", response_model=UserList)
async def list_users(_: AdminOnly, session: SessionDep) -> UserList:
    rows = (
        await session.scalars(select(User).order_by(User.created_at.desc()))
    ).all()
    return UserList(
        items=[
            UserListItem(
                id=u.id, email=u.email, role=u.role, full_name=u.full_name,
                active=u.active, created_at=u.created_at.isoformat(),
            )
            for u in rows
        ],
        total=len(rows),
    )


@router.patch("/users/{user_id}/active", response_model=CurrentUser)
async def set_active(
    user_id: UUID,
    payload: SetActiveIn,
    request: Request,
    actor: AdminOnly,
    session: SessionDep,
) -> CurrentUser:
    if user_id == actor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="cannot deactivate yourself")
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    was = target.active
    target.active = payload.active
    await session.flush()
    await audit_svc.append(
        session,
        actor_id=actor.id,
        action="user.active_changed",
        resource_type="user",
        resource_id=str(target.id),
        payload={
            "from": was,
            "to": payload.active,
            "target_email": target.email,
            "ip": request.client.host if request.client else None,
        },
    )
    await session.commit()
    return CurrentUser(
        id=target.id, email=target.email, role=target.role, full_name=target.full_name,
    )


@router.get("/stats", response_model=SystemStats)
async def system_stats(_: AdminOnly, session: SessionDep) -> SystemStats:
    users_total = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    users_active = int(
        await session.scalar(select(func.count()).select_from(User).where(User.active.is_(True))) or 0
    )
    rec_total = int(await session.scalar(select(func.count()).select_from(Recording)) or 0)
    rec_active = int(
        await session.scalar(
            select(func.count()).select_from(Recording).where(Recording.deleted_at.is_(None))
        ) or 0
    )
    profiles_total = int(await session.scalar(select(func.count()).select_from(VoiceProfile)) or 0)
    syn_total = int(await session.scalar(select(func.count()).select_from(Synthesis)) or 0)
    rows = (
        await session.execute(
            select(Synthesis.status, func.count()).group_by(Synthesis.status)
        )
    ).all()
    by_status = {
        s.value if isinstance(s, SynthesisStatus) else str(s): int(c)
        for s, c in rows
    }
    return SystemStats(
        users_total=users_total,
        users_active=users_active,
        recordings_total=rec_total,
        recordings_active=rec_active,
        profiles_total=profiles_total,
        syntheses_total=syn_total,
        syntheses_by_status=by_status,
    )
