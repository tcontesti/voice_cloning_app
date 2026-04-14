from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.synthesis import Synthesis, SynthesisModel, SynthesisStatus
from app.db.models.user import User

MAX_TEXT_CHARS = 500


def _sanitize_text(text: str) -> str:
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    return cleaned.strip()


async def create_job(
    session: AsyncSession,
    *,
    user: User,
    profile_id: UUID,
    model: SynthesisModel,
    text: str,
    options: dict | None = None,
) -> Synthesis:
    text = _sanitize_text(text)
    if not text:
        raise ValueError("text is empty")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text exceeds {MAX_TEXT_CHARS} chars")

    syn = Synthesis(
        user_id=user.id,
        profile_id=profile_id,
        model=model,
        text=text,
        options=options or {},
        status=SynthesisStatus.queued,
    )
    session.add(syn)
    await session.flush()
    return syn


async def get_owned(
    session: AsyncSession, *, user_id: UUID, synthesis_id: UUID
) -> Synthesis | None:
    syn = await session.get(Synthesis, synthesis_id)
    if syn is None or syn.user_id != user_id:
        return None
    return syn


async def list_for_user(session: AsyncSession, *, user_id: UUID, limit: int = 50) -> list[Synthesis]:
    rows = await session.scalars(
        select(Synthesis)
        .where(Synthesis.user_id == user_id)
        .order_by(Synthesis.created_at.desc())
        .limit(limit)
    )
    return list(rows.all())
