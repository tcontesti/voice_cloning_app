"""Tests for /profiles, /synthesis, /synthesis/models endpoints.

Celery's send_task is mocked so we don't need a broker; this verifies the
ENQUEUE side (DB row created, audit row appended, send_task called with the
right kwargs/queue). Worker-side execution is covered by integration smoke
on the Spark, not by these unit tests.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.user import UserRole
from app.db.session import get_session
from app.main import app
from app.services import audit_log as audit_svc
from app.services import storage
from app.services import users as users_svc
from tests.fixtures import audio as audio_fx

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def _override():
        yield session

    app.dependency_overrides[get_session] = _override

    bucket = f"test-rec-{id(session)}"
    s = get_settings()
    original = s.minio_bucket_recordings
    s.minio_bucket_recordings = bucket  # type: ignore[misc]
    try:
        with storage.temporary_bucket(bucket):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac
    finally:
        s.minio_bucket_recordings = original  # type: ignore[misc]
        app.dependency_overrides.clear()


async def _login(client: AsyncClient, session: AsyncSession, role=UserRole.paciente):
    user = await users_svc.create(
        session, email=f"{role.value}@example.com", password="pw1234", role=role
    )
    tok = (
        await client.post("/auth/login", json={"email": user.email, "password": "pw1234"})
    ).json()["access_token"]
    return user, {"Authorization": f"Bearer {tok}"}


async def _upload_recording(client: AsyncClient, headers: dict) -> str:
    r = await client.post(
        "/recordings",
        headers=headers,
        files={"file": ("ref.wav", audio_fx.speechlike_wav(duration_s=3.0), "audio/wav")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_models_endpoint_lists_chatterbox_available(client: AsyncClient) -> None:
    r = await client.get("/synthesis/models")
    assert r.status_code == 200
    body = r.json()
    chat = next(m for m in body if m["name"] == "chatterbox")
    assert chat["available"] is True
    omni = next(m for m in body if m["name"] == "omnivoice")
    assert omni["available"] is True
    qwen = next(m for m in body if m["name"] == "qwen3tts")
    assert qwen["available"] is True


async def test_create_profile_owns_references(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    rec_id = await _upload_recording(client, headers)
    r = await client.post(
        "/profiles",
        headers=headers,
        json={"name": "Mi voz", "reference_ids": [rec_id]},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Mi voz"
    assert body["reference_ids"] == [rec_id]
    rows = await audit_svc.list_all(session)
    assert any(r.action == "profile.created" for r in rows)


async def test_create_profile_rejects_other_users_reference(
    client: AsyncClient, session: AsyncSession
) -> None:
    user_a, headers_a = await _login(client, session, UserRole.paciente)
    user_b = await users_svc.create(
        session, email="b@example.com", password="pw1234", role=UserRole.paciente
    )
    tok_b = (await client.post("/auth/login",
                                 json={"email": user_b.email, "password": "pw1234"})).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {tok_b}"}
    rec_b = await _upload_recording(client, headers_b)

    # user_a tries to use user_b's reference
    r = await client.post(
        "/profiles",
        headers=headers_a,
        json={"name": "Robo", "reference_ids": [rec_b]},
    )
    assert r.status_code == 400


async def test_create_synthesis_enqueues_celery_and_audits(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    rec_id = await _upload_recording(client, headers)
    profile = (await client.post(
        "/profiles", headers=headers,
        json={"name": "auto", "reference_ids": [rec_id]},
    )).json()

    with patch("app.workers.celery_app.celery_app.send_task") as send:
        r = await client.post(
            "/synthesis",
            headers=headers,
            json={
                "profile_id": profile["id"],
                "model": "chatterbox",
                "text": "Hola, esto es una prueba clínica.",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "queued"
        assert body["model"] == "chatterbox"

        send.assert_called_once()
        kwargs = send.call_args.kwargs
        assert kwargs["queue"] == "synth.chatterbox"
        assert kwargs["kwargs"]["synthesis_id"] == body["id"]
        assert kwargs["kwargs"]["model"] == "chatterbox"

    rows = await audit_svc.list_all(session)
    assert any(r.action == "synthesis.queued" for r in rows)


async def test_create_synthesis_routes_omnivoice_to_its_queue(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    rec_id = await _upload_recording(client, headers)
    profile = (await client.post(
        "/profiles", headers=headers,
        json={"name": "auto", "reference_ids": [rec_id]},
    )).json()

    with patch("app.workers.celery_app.celery_app.send_task") as send:
        r = await client.post(
            "/synthesis", headers=headers,
            json={"profile_id": profile["id"], "model": "omnivoice", "text": "Hola."},
        )
        assert r.status_code == 201
        assert send.call_args.kwargs["queue"] == "synth.omnivoice"
        assert send.call_args.kwargs["kwargs"]["model"] == "omnivoice"


async def test_create_synthesis_rejects_text_too_long(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    rec_id = await _upload_recording(client, headers)
    profile = (await client.post(
        "/profiles", headers=headers,
        json={"name": "auto", "reference_ids": [rec_id]},
    )).json()
    r = await client.post(
        "/synthesis",
        headers=headers,
        json={
            "profile_id": profile["id"],
            "model": "chatterbox",
            "text": "x" * 501,
        },
    )
    assert r.status_code == 422  # pydantic max_length


async def test_create_synthesis_rejects_other_users_profile(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers_a = await _login(client, session)
    user_b = await users_svc.create(
        session, email="other@example.com", password="pw1234", role=UserRole.paciente
    )
    tok_b = (await client.post(
        "/auth/login", json={"email": user_b.email, "password": "pw1234"}
    )).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {tok_b}"}
    rec_b = await _upload_recording(client, headers_b)
    profile_b = (await client.post(
        "/profiles", headers=headers_b,
        json={"name": "auto", "reference_ids": [rec_b]},
    )).json()

    r = await client.post(
        "/synthesis",
        headers=headers_a,
        json={"profile_id": profile_b["id"], "model": "chatterbox", "text": "test"},
    )
    assert r.status_code == 404


async def test_audit_chain_remains_consistent_after_synthesis_workflow(
    client: AsyncClient, session: AsyncSession
) -> None:
    """End-to-end: every endpoint we touched here adds a row; chain still verifies."""
    from app.core.audit import verify_chain

    _, headers = await _login(client, session)
    rec_id = await _upload_recording(client, headers)
    profile = (await client.post(
        "/profiles", headers=headers,
        json={"name": "auto", "reference_ids": [rec_id]},
    )).json()
    with patch("app.workers.celery_app.celery_app.send_task"):
        await client.post(
            "/synthesis", headers=headers,
            json={"profile_id": profile["id"], "model": "chatterbox", "text": "x"},
        )

    rows = await audit_svc.list_all(session)
    ok, broken = verify_chain(rows)
    assert ok, f"chain broke at {broken}"
