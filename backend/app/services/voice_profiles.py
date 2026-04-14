from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recording import Recording
from app.db.models.user import User
from app.db.models.voice_profile import ProfileStatus, VoiceProfile


async def create_for_references(
    session: AsyncSession,
    *,
    user: User,
    name: str,
    reference_ids: list[UUID],
) -> VoiceProfile:
    rows = (
        await session.scalars(
            select(Recording).where(
                Recording.id.in_(reference_ids),
                Recording.user_id == user.id,
                Recording.deleted_at.is_(None),
            )
        )
    ).all()
    if len(rows) != len(reference_ids):
        raise ValueError("one or more references missing or not owned by user")

    profile = VoiceProfile(
        user_id=user.id,
        name=name,
        reference_ids=list(reference_ids),
        status=ProfileStatus.ready,
    )
    session.add(profile)
    await session.flush()
    return profile


async def list_for_user(session: AsyncSession, *, user_id: UUID) -> list[VoiceProfile]:
    rows = await session.scalars(
        select(VoiceProfile)
        .where(VoiceProfile.user_id == user_id)
        .order_by(VoiceProfile.created_at.desc())
    )
    return list(rows.all())


async def get_owned(
    session: AsyncSession, *, user_id: UUID, profile_id: UUID
) -> VoiceProfile | None:
    p = await session.get(VoiceProfile, profile_id)
    if p is None or p.user_id != user_id:
        return None
    return p
