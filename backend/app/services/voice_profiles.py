from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recording import Recording
from app.db.models.synthesis import Synthesis
from app.db.models.user import User
from app.db.models.voice_profile import ProfileStatus, VoiceProfile


class ProfileInUseError(Exception):
    """Raised when delete is requested but syntheses still reference the profile."""


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


async def rename(
    session: AsyncSession, *, profile: VoiceProfile, name: str
) -> VoiceProfile:
    profile.name = name
    await session.flush()
    return profile


async def set_references(
    session: AsyncSession,
    *,
    user: User,
    profile: VoiceProfile,
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
    profile.reference_ids = list(reference_ids)
    await session.flush()
    return profile


async def count_syntheses(
    session: AsyncSession, *, profile_id: UUID
) -> int:
    n = await session.scalar(
        select(func.count()).select_from(Synthesis).where(Synthesis.profile_id == profile_id)
    )
    return int(n or 0)


async def delete(
    session: AsyncSession, *, profile: VoiceProfile
) -> None:
    # Syntheses FK is RESTRICT, so we'd 500 on the underlying IntegrityError
    # without this pre-check. Give the caller a clean conflict instead.
    n = await count_syntheses(session, profile_id=profile.id)
    if n > 0:
        raise ProfileInUseError(
            f"profile in use by {n} synthesis row(s)",
        )
    await session.delete(profile)
    await session.flush()


async def cascade_delete(
    session: AsyncSession, *, profile: VoiceProfile
) -> int:
    """Drop every synthesis tied to the profile, then the profile itself.

    Returns the number of synthesis rows deleted so the caller can surface
    it (and audit it) without an extra round-trip. Audio blobs in MinIO
    are left behind — they're uniquely keyed per synthesis and a MinIO
    lifecycle policy or manual sweep can reclaim them later. Blocking
    the DB delete on a MinIO round-trip that might fail isn't worth the
    cross-system coupling.
    """
    n = await count_syntheses(session, profile_id=profile.id)
    if n > 0:
        # Bulk delete syntheses first, then the profile. Single transaction
        # — if anything raises, the caller hasn't committed yet.
        from sqlalchemy import delete as sa_delete
        await session.execute(
            sa_delete(Synthesis).where(Synthesis.profile_id == profile.id)
        )
    await session.delete(profile)
    await session.flush()
    return n
