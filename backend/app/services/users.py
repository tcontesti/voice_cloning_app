from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models.user import User, UserRole


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower()))


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_by_email(session, email)
    if user is None or not user.active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    role: UserRole,
    full_name: str | None = None,
) -> User:
    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        role=role,
        full_name=full_name,
    )
    session.add(user)
    await session.flush()
    return user
