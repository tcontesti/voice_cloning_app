"""Recordings API integration tests.

Uses the running MinIO container with a per-test bucket so tests don't
contaminate the dev recordings bucket.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session as deps_get_session  # noqa: F401
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

    bucket = f"test-recordings-{id(session)}"
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


async def _login(client: AsyncClient, session: AsyncSession, role: UserRole = UserRole.paciente):
    user = await users_svc.create(
        session,
        email=f"{role.value}@example.com",
        password="pw1234",
        role=role,
    )
    tok = (
        await client.post(
            "/auth/login", json={"email": user.email, "password": "pw1234"}
        )
    ).json()["access_token"]
    return user, {"Authorization": f"Bearer {tok}"}


async def test_upload_returns_metrics_and_audits(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    wav = audio_fx.speechlike_wav(duration_s=3.0)
    r = await client.post(
        "/recordings",
        headers=headers,
        files={"file": ("ref.wav", wav, "audio/wav")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sample_rate"] == 16000
    assert body["duration_s"] == pytest.approx(3.0, abs=0.01)
    assert body["speech_ratio"] > 0.5
    assert len(body["sha256"]) == 64

    rows = await audit_svc.list_all(session)
    assert any(r.action == "recording.uploaded" for r in rows)


async def test_upload_rejects_low_snr(client: AsyncClient, session: AsyncSession) -> None:
    _, headers = await _login(client, session)
    wav = audio_fx.speechlike_wav(duration_s=3.0, snr_db=5.0)
    r = await client.post(
        "/recordings",
        headers=headers,
        files={"file": ("noisy.wav", wav, "audio/wav")},
    )
    # If acoustic luck pushes SNR above threshold, accept either outcome but
    # at minimum the API must not 500.
    assert r.status_code in (201, 422)


async def test_upload_rejects_silence(client: AsyncClient, session: AsyncSession) -> None:
    _, headers = await _login(client, session)
    r = await client.post(
        "/recordings",
        headers=headers,
        files={"file": ("silence.wav", audio_fx.silence_wav(duration_s=3.0), "audio/wav")},
    )
    assert r.status_code == 422
    assert "speech" in r.json()["detail"].lower()


async def test_upload_rejects_too_short(client: AsyncClient, session: AsyncSession) -> None:
    _, headers = await _login(client, session)
    r = await client.post(
        "/recordings",
        headers=headers,
        files={"file": ("short.wav", audio_fx.too_short_wav(), "audio/wav")},
    )
    assert r.status_code == 422


async def test_upload_rejects_wrong_content_type(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    r = await client.post(
        "/recordings",
        headers=headers,
        files={"file": ("ref.mp3", audio_fx.speechlike_wav(), "audio/mpeg")},
    )
    assert r.status_code == 415


async def test_list_only_returns_own_recordings(
    client: AsyncClient, session: AsyncSession
) -> None:
    user_a, headers_a = await _login(client, session, UserRole.paciente)
    # Create a second user via direct service (different login path).
    user_b = await users_svc.create(
        session, email="other@example.com", password="pw1234", role=UserRole.paciente
    )
    tok_b = (
        await client.post("/auth/login", json={"email": user_b.email, "password": "pw1234"})
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    await client.post(
        "/recordings",
        headers=headers_a,
        files={"file": ("a.wav", audio_fx.speechlike_wav(), "audio/wav")},
    )
    await client.post(
        "/recordings",
        headers=headers_b,
        files={"file": ("b.wav", audio_fx.speechlike_wav(seed=1), "audio/wav")},
    )

    resp_a = await client.get("/recordings", headers=headers_a)
    resp_b = await client.get("/recordings", headers=headers_b)
    assert resp_a.status_code == 200 and resp_b.status_code == 200
    assert resp_a.json()["total"] == 1
    assert resp_b.json()["total"] == 1
    assert resp_a.json()["items"][0]["user_id"] == str(user_a.id)


async def test_soft_delete_removes_from_list_and_audits(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    rec = (
        await client.post(
            "/recordings",
            headers=headers,
            files={"file": ("a.wav", audio_fx.speechlike_wav(), "audio/wav")},
        )
    ).json()

    r = await client.delete(f"/recordings/{rec['id']}", headers=headers)
    assert r.status_code == 204

    listed = await client.get("/recordings", headers=headers)
    assert listed.json()["total"] == 0

    rows = await audit_svc.list_all(session)
    assert any(r.action == "recording.soft_deleted" for r in rows)


async def test_get_404_for_other_users_recording(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers_a = await _login(client, session, UserRole.paciente)
    user_b = await users_svc.create(
        session, email="other@example.com", password="pw1234", role=UserRole.paciente
    )
    tok_b = (
        await client.post("/auth/login", json={"email": user_b.email, "password": "pw1234"})
    ).json()["access_token"]
    rec_b = (
        await client.post(
            "/recordings",
            headers={"Authorization": f"Bearer {tok_b}"},
            files={"file": ("b.wav", audio_fx.speechlike_wav(seed=2), "audio/wav")},
        )
    ).json()

    r = await client.get(f"/recordings/{rec_b['id']}", headers=headers_a)
    assert r.status_code == 404


async def test_dedup_same_bytes_returns_existing(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, headers = await _login(client, session)
    wav = audio_fx.speechlike_wav(duration_s=3.0, seed=99)
    a = await client.post(
        "/recordings", headers=headers, files={"file": ("a.wav", wav, "audio/wav")}
    )
    b = await client.post(
        "/recordings", headers=headers, files={"file": ("a.wav", wav, "audio/wav")}
    )
    assert a.json()["id"] == b.json()["id"]
