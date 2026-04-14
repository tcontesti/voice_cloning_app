"""OIDC JWT verification via JWKS (production path).

When AUTH_MODE=keycloak the backend verifies RS256 tokens issued by Keycloak
using the realm's public keys fetched from OIDC_JWKS_URL. Keys are cached
in memory for 1 hour; if a kid miss occurs we re-fetch to handle rotation.

When AUTH_MODE=mock the backend falls back to local HS256 (see security.py);
this file is dormant in that case.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from jose import jwt
from jose.exceptions import JWTError

from app.core.config import get_settings

_jwks_cache: dict[str, Any] | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_S = 3600.0


def _fetch_jwks(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as r:  # noqa: S310 — configured URL
        return json.loads(r.read().decode("utf-8"))


def _get_jwks(force: bool = False) -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at
    s = get_settings()
    if not s.oidc_jwks_url:
        raise RuntimeError("OIDC_JWKS_URL not configured")
    now = time.time()
    if _jwks_cache is None or force or (now - _jwks_fetched_at) > _JWKS_TTL_S:
        _jwks_cache = _fetch_jwks(s.oidc_jwks_url)
        _jwks_fetched_at = now
    return _jwks_cache


def _key_for(kid: str) -> dict[str, Any]:
    jwks = _get_jwks()
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return k
    # Rotation — refetch once.
    jwks = _get_jwks(force=True)
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            return k
    raise ValueError(f"kid {kid} not found in JWKS")


def decode_oidc(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        kid = header["kid"]
        key = _key_for(kid)
        claims = jwt.decode(
            token, key,
            algorithms=[header.get("alg", "RS256")],
            audience=s.oidc_audience or None,
            issuer=s.oidc_issuer or None,
            options={"verify_aud": bool(s.oidc_audience)},
        )
        return claims
    except JWTError as e:
        raise ValueError(f"invalid oidc token: {e}") from e
