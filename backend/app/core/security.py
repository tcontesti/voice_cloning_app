"""JWT minting/validation + password hashing.

Mock-OIDC style: HS256 JWT signed with APP_SECRET_KEY. Same claim names
Keycloak emits (sub, email, preferred_username, realm_access.roles) so M8
swap is mechanical.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(hours=8)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(*, user_id: UUID, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "email": email,
        "preferred_username": email,
        "realm_access": {"roles": [role]},
        "iat": int(now.timestamp()),
        "exp": int((now + ACCESS_TOKEN_TTL).timestamp()),
    }
    return jwt.encode(claims, get_settings().app_secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Validate a token using the configured auth mode.

    AUTH_MODE=mock      → HS256 with APP_SECRET_KEY (dev / fallback).
    AUTH_MODE=keycloak  → RS256 verified against Keycloak JWKS.
    """
    mode = get_settings().auth_mode
    if mode == "keycloak":
        from app.core.oidc import decode_oidc
        return decode_oidc(token)
    try:
        return jwt.decode(token, get_settings().app_secret_key, algorithms=[ALGORITHM])
    except JWTError as e:
        raise ValueError(f"invalid token: {e}") from e
