from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.db.models.user import User, UserRole
from app.db.session import get_session

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _role_from_keycloak_claims(claims: dict) -> UserRole:
    """Pick the first known role from realm_access.roles."""
    roles = (claims.get("realm_access") or {}).get("roles") or []
    for candidate in ("admin", "auditor", "clinico", "paciente"):
        if candidate in roles:
            return UserRole(candidate)
    return UserRole.paciente  # safest default


async def _jit_provision(session: AsyncSession, claims: dict) -> User:
    """Just-in-time provision on first Keycloak login."""
    email = (claims.get("email") or claims.get("preferred_username") or "").lower()
    if not email:
        raise ValueError("token has no email")
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        return existing
    from app.core.security import hash_password
    user = User(
        email=email,
        hashed_password=hash_password("!keycloak-managed!"),  # never used
        role=_role_from_keycloak_claims(claims),
        full_name=claims.get("name"),
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return user


async def current_user(
    token: Annotated[str, Depends(oauth2)],
    session: SessionDep,
) -> User:
    try:
        claims = decode_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Mock mode: sub is our internal UUID. Keycloak mode: sub is the KC user
    # id (UUID string); we match by email and JIT-provision if unseen.
    if get_settings().auth_mode == "keycloak":
        try:
            user = await _jit_provision(session, claims)
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"provision failed: {e}") from e
    else:
        user = await session.get(User, UUID(claims["sub"]))

    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user inactive")
    return user


CurrentUserDep = Annotated[User, Depends(current_user)]


def require_roles(*roles: UserRole):
    async def _checker(user: CurrentUserDep) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return _checker
