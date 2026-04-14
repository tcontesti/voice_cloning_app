"""Consent service.

The consent text lives under app/consent_texts/ as versioned markdown so it
is auditable in git. text_hash = sha256 of the raw bytes; the client must
echo the same hash they saw to prevent legal-text/UI desync attacks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.consent import Consent
from app.db.models.user import User

CURRENT_CONSENT_VERSION = "v1-2026-04-14-DRAFT"
_CONSENT_DIR = Path(__file__).resolve().parent.parent / "consent_texts"


@dataclass(frozen=True)
class ConsentText:
    version: str
    body_markdown: str
    text_hash: str


def load_current() -> ConsentText:
    path = _CONSENT_DIR / f"{CURRENT_CONSENT_VERSION}.md"
    body = path.read_text(encoding="utf-8")
    h = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return ConsentText(version=CURRENT_CONSENT_VERSION, body_markdown=body, text_hash=h)


def compute_signature(*, user: User, text_hash: str, ip: str | None) -> str:
    """Deterministic signature for the consent event.

    Hash of (user_id || email || version_text_hash || ip-or-empty).
    Bound to the user identity AND the exact text version, so re-signing
    a different version produces a distinct signature_hash.
    """
    h = hashlib.sha256()
    h.update(str(user.id).encode())
    h.update(b"|")
    h.update(user.email.encode())
    h.update(b"|")
    h.update(text_hash.encode())
    h.update(b"|")
    h.update((ip or "").encode())
    return h.hexdigest()


async def record_signature(
    session: AsyncSession,
    *,
    user: User,
    version: str,
    text_hash: str,
    ip: str | None,
    user_agent: str | None,
) -> Consent:
    sig = compute_signature(user=user, text_hash=text_hash, ip=ip)
    entry = Consent(
        user_id=user.id,
        version=version,
        text_hash=text_hash,
        signature_hash=sig,
        ip=ip,
        user_agent=(user_agent or "")[:512] or None,
    )
    session.add(entry)
    await session.flush()
    return entry
