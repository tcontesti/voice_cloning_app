"""Audit log hash chain tests — append, verify, tampering detection."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import GENESIS_PREV_HASH, verify_chain
from app.services import audit_log as audit_svc

pytestmark = pytest.mark.asyncio


async def _append_n(session: AsyncSession, n: int) -> list:
    actor = uuid4()
    rows = []
    for i in range(n):
        e = await audit_svc.append(
            session,
            actor_id=actor,
            action="test.append",
            resource_type="test",
            resource_id=str(i),
            payload={"i": i},
        )
        rows.append(e)
    await session.flush()
    return rows


async def test_genesis_prev_hash(session: AsyncSession) -> None:
    rows = await _append_n(session, 1)
    assert rows[0].prev_hash == GENESIS_PREV_HASH
    assert len(rows[0].hash) == 64


async def test_chain_links_consecutive_entries(session: AsyncSession) -> None:
    rows = await _append_n(session, 5)
    for i in range(1, 5):
        assert rows[i].prev_hash == rows[i - 1].hash


async def test_verify_chain_passes_on_clean_chain(session: AsyncSession) -> None:
    await _append_n(session, 10)
    all_rows = await audit_svc.list_all(session)
    ok, broken = verify_chain(all_rows)
    assert ok is True
    assert broken is None


async def test_verify_chain_detects_payload_tampering(session: AsyncSession) -> None:
    """Mutating any field of any row must break verification at that row.

    Simulates a privileged attacker bypassing the append-only trigger via
    `session_replication_role = replica`. The hash chain still flags the
    tampering because the recomputed hash won't match.
    """
    rows = await _append_n(session, 5)
    await session.execute(text("SET session_replication_role = replica"))
    await session.execute(
        text("UPDATE audit.audit_log SET payload = CAST(:p AS jsonb) WHERE id = :id").bindparams(
            p='{"i": 999}', id=rows[2].id
        )
    )
    await session.execute(text("SET session_replication_role = origin"))
    await session.flush()
    for r in rows:
        await session.refresh(r)

    ok, broken = verify_chain(rows)
    assert ok is False
    assert broken == rows[2].id


async def test_append_only_trigger_blocks_update(session: AsyncSession) -> None:
    await _append_n(session, 1)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text("UPDATE audit.audit_log SET action = 'tampered'"))
        await session.flush()


async def test_append_only_trigger_blocks_delete(session: AsyncSession) -> None:
    await _append_n(session, 1)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text("DELETE FROM audit.audit_log"))
        await session.flush()


async def test_appends_produce_unique_hashes(session: AsyncSession) -> None:
    rows = await _append_n(session, 50)
    hashes = {r.hash for r in rows}
    assert len(hashes) == 50
