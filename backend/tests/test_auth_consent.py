"""Integration tests: auth + consent + audit linkage.

Uses TestClient against the FastAPI app, but overrides get_session so it
uses our test transactional session and rolls back.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.db.models.user import UserRole
from app.db.session import get_session
from app.main import app
from app.services import audit_log as audit_svc
from app.services import consent as consent_svc
from app.services import users as users_svc

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncClient:
    async def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _make_user(session: AsyncSession, role: UserRole, password: str = "pw"):
    return await users_svc.create(
        session,
        email=f"{role.value}@example.com",
        password=password,
        role=role,
    )


async def test_login_success_returns_token(client: AsyncClient, session: AsyncSession) -> None:
    await _make_user(session, UserRole.paciente, password="pw1234")
    r = await client.post("/auth/login", json={"email": "paciente@example.com", "password": "pw1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


async def test_login_failure_audited(client: AsyncClient, session: AsyncSession) -> None:
    r = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 401
    rows = await audit_svc.list_all(session)
    assert any(row.action == "auth.login.failed" for row in rows)


async def test_me_requires_token(client: AsyncClient) -> None:
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_with_token_ok(client: AsyncClient, session: AsyncSession) -> None:
    await _make_user(session, UserRole.clinico, password="pw1234")
    tok = (
        await client.post(
            "/auth/login", json={"email": "clinico@example.com", "password": "pw1234"}
        )
    ).json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["email"] == "clinico@example.com"
    assert r.json()["role"] == "clinico"


async def test_consent_current_returns_text_and_hash(client: AsyncClient) -> None:
    r = await client.get("/consent/current")
    assert r.status_code == 200
    body = r.json()
    assert len(body["text_hash"]) == 64
    assert body["version"].startswith("v")
    assert "Hospital Universitario Son Llatzer" in body["body_markdown"]


async def test_consent_accept_records_signature_and_audit(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await _make_user(session, UserRole.paciente, password="pw1234")
    tok = (
        await client.post(
            "/auth/login", json={"email": user.email, "password": "pw1234"}
        )
    ).json()["access_token"]
    current = consent_svc.load_current()

    r = await client.post(
        "/consent/accept",
        headers={"Authorization": f"Bearer {tok}"},
        json={"version": current.version, "text_hash": current.text_hash},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["text_hash"] == current.text_hash
    assert len(body["signature_hash"]) == 64

    rows = await audit_svc.list_all(session)
    assert any(row.action == "consent.accepted" for row in rows)


async def test_consent_accept_rejects_text_drift(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await _make_user(session, UserRole.paciente, password="pw1234")
    tok = (
        await client.post(
            "/auth/login", json={"email": user.email, "password": "pw1234"}
        )
    ).json()["access_token"]
    r = await client.post(
        "/consent/accept",
        headers={"Authorization": f"Bearer {tok}"},
        json={"version": "v1-2026-04-14-DRAFT", "text_hash": "f" * 64},
    )
    assert r.status_code == 409


async def test_audit_endpoint_requires_admin_or_auditor(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await _make_user(session, UserRole.paciente, password="pw1234")
    tok = (
        await client.post(
            "/auth/login", json={"email": user.email, "password": "pw1234"}
        )
    ).json()["access_token"]
    r = await client.get("/audit/logs", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


async def test_audit_verify_endpoint_returns_ok_for_clean_chain(
    client: AsyncClient, session: AsyncSession
) -> None:
    auditor = await _make_user(session, UserRole.auditor, password="pw1234")
    tok = (
        await client.post(
            "/auth/login", json={"email": auditor.email, "password": "pw1234"}
        )
    ).json()["access_token"]
    r = await client.get("/audit/verify", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["broken_at"] is None
    assert body["total_entries"] >= 1  # the auditor's own login is logged
