"""Audit log hash chain primitives.

Each entry's hash is sha256 over a canonical representation that includes the
previous entry's hash. Tampering with any field of any row breaks the chain
from that row onward.

Genesis prev_hash is 64 zeros.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

GENESIS_PREV_HASH = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(
    *,
    prev_hash: str,
    actor_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    payload: dict[str, Any],
    created_at: datetime,
) -> str:
    """Deterministic hash for one audit row, given its predecessor's hash."""
    canonical = _canonical(
        {
            "prev_hash": prev_hash,
            "actor_id": str(actor_id) if actor_id is not None else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "payload": payload,
            "created_at": created_at.isoformat(),
        }
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_chain(rows: list[Any]) -> tuple[bool, int | None]:
    """Verify a list of AuditLog rows ordered by id ASC.

    Returns (ok, broken_id). broken_id is the row.id of the first row whose
    stored hash does not match its recomputed hash, or whose prev_hash does
    not match the previous row's hash.
    """
    expected_prev = GENESIS_PREV_HASH
    for row in rows:
        if row.prev_hash != expected_prev:
            return False, row.id
        recomputed = compute_entry_hash(
            prev_hash=row.prev_hash,
            actor_id=row.actor_id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            payload=row.payload,
            created_at=row.created_at,
        )
        if recomputed != row.hash:
            return False, row.id
        expected_prev = row.hash
    return True, None
