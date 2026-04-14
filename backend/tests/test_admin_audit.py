"""Admin + audit panel tests: role gating, filters, stats."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import UserRole
from app.db.session import get_session
from app.main import app
from app.services import users as users_svc

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login_as(client: AsyncClient, session: AsyncSession, role: UserRole):
    u = await users_svc.create(
        session, email=f"{role.value}@example.com", password="pw1234", role=role
    )
    tok = (
        await client.post("/auth/login", json={"email": u.email, "password": "pw1234"})
    ).json()["access_token"]
    return u, {"Authorization": f"Bearer {tok}"}


# ── /admin ─────────────────────────────────────────────────────────────────

async def test_admin_users_requires_admin_role(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login_as(client, session, UserRole.auditor)
    r = await client.get("/admin/users", headers=headers)
    assert r.status_code == 403


async def test_admin_users_lists_all(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, admin_headers = await _login_as(client, session, UserRole.admin)
    await users_svc.create(session, email="p@example.com", password="pw",
                           role=UserRole.paciente)
    r = await client.get("/admin/users", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 2


async def test_admin_cannot_deactivate_self(
    client: AsyncClient, session: AsyncSession
) -> None:
    admin, headers = await _login_as(client, session, UserRole.admin)
    r = await client.patch(f"/admin/users/{admin.id}/active",
                             headers=headers, json={"active": False})
    assert r.status_code == 400


async def test_admin_can_deactivate_other_user_and_is_audited(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, admin_headers = await _login_as(client, session, UserRole.admin)
    target = await users_svc.create(
        session, email="target@example.com", password="pw", role=UserRole.paciente
    )
    r = await client.patch(f"/admin/users/{target.id}/active",
                             headers=admin_headers, json={"active": False})
    assert r.status_code == 200

    # Target can no longer log in
    bad = await client.post("/auth/login",
                              json={"email": target.email, "password": "pw"})
    assert bad.status_code == 401

    from app.services import audit_log as audit_svc
    rows = await audit_svc.list_all(session)
    assert any(r.action == "user.active_changed" for r in rows)


async def test_admin_stats_returns_counts(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login_as(client, session, UserRole.admin)
    r = await client.get("/admin/stats", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["users_total"] >= 1
    assert "syntheses_by_status" in body


# ── /audit filters ─────────────────────────────────────────────────────────

async def test_audit_logs_filters_by_action(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, auditor_headers = await _login_as(client, session, UserRole.auditor)
    # Generate some events through user actions
    r = await client.get(
        "/audit/logs",
        headers=auditor_headers,
        params={"action": "auth.login.ok"},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["action"] == "auth.login.ok"


async def test_audit_logs_filters_by_action_prefix(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login_as(client, session, UserRole.auditor)
    r = await client.get(
        "/audit/logs",
        headers=headers,
        params={"action_prefix": "auth."},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["action"].startswith("auth.")


async def test_audit_stats_returns_aggregates(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login_as(client, session, UserRole.auditor)
    r = await client.get("/audit/stats", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert "by_action" in body and "by_resource" in body


async def test_audit_logs_include_payload_for_auditor(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login_as(client, session, UserRole.auditor)
    r = await client.get("/audit/logs", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert "payload" in items[0]


async def test_paciente_cannot_access_audit_endpoints(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login_as(client, session, UserRole.paciente)
    for path in ("/audit/logs", "/audit/verify", "/audit/stats"):
        r = await client.get(path, headers=headers)
        assert r.status_code == 403, path
