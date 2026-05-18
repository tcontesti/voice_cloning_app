#!/usr/bin/env python
"""Smoke enqueue: synth one job end-to-end, no UI, no auth.

Usage (from voice_cloning_app/ with the main venv):
    ~/voice_cloning_env/.venv/bin/python worker/smoke_enqueue.py \
        --model chatterbox \
        --text "Hola, prueba clínica." \
        --ref  /home/SPARK_USER/voice_cloning/datasets/reference_clips/spk01_male_10s.wav

What it does:
    1. Reads the ref WAV, sha256s it, uploads to MinIO under `recordings/`.
    2. Upserts a smoke user + recording row + voice_profile in Postgres.
    3. Inserts a synthesis row (status=queued) and Celery-dispatches the
       synthesize task to the right per-model queue.
    4. Polls the synthesis row every 2 s until status terminal.
    5. Prints s3_key_output + watermark_verified + aasist_score.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from uuid import UUID

# Ensure services resolve via the Spark's loopback (docker-compose ports)
# when the script runs natively. Do this BEFORE any app imports.
for var, default in (
    ("POSTGRES_HOST", "localhost"),
    ("REDIS_HOST", "localhost"),
    ("RABBITMQ_HOST", "localhost"),
    ("MINIO_HOST", "localhost"),
):
    os.environ.setdefault(var, default)

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT / "backend"))

# Source creds from the worker env file if nothing is pre-set.
_wenv = Path.home() / ".config" / "vcapp" / "worker.env"
if _wenv.exists():
    for line in _wenv.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.models.recording import Recording  # noqa: E402
from app.db.models.synthesis import Synthesis, SynthesisModel, SynthesisStatus  # noqa: E402
from app.db.models.user import User, UserRole  # noqa: E402
from app.db.models.voice_profile import VoiceProfile  # noqa: E402
from app.services import storage  # noqa: E402


SMOKE_EMAIL = "smoke@example.com"
POLL_INTERVAL_S = 2.0


def _sync_session() -> Session:
    s = get_settings()
    url = (
        f"postgresql+psycopg2://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{s.postgres_db}"
    )
    engine = create_engine(url, pool_pre_ping=True, future=True)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _ensure_user(db: Session) -> User:
    u = db.scalar(select(User).where(User.email == SMOKE_EMAIL))
    if u is not None:
        return u
    from app.core.security import hash_password
    u = User(
        email=SMOKE_EMAIL,
        hashed_password=hash_password("smoke"),
        role=UserRole.paciente,
        full_name="Smoke Test",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _ensure_recording(db: Session, user: User, ref_path: Path) -> Recording:
    raw = ref_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    rec = db.scalar(
        select(Recording).where(
            Recording.user_id == user.id,
            Recording.sha256 == sha,
            Recording.deleted_at.is_(None),
        )
    )
    if rec is not None:
        return rec

    s3_key = f"users/{user.id}/refs/smoke-{sha[:16]}.wav"
    storage.put_object(
        bucket=get_settings().minio_bucket_recordings,
        key=s3_key,
        data=raw,
        content_type="audio/wav",
    )
    import soundfile as sf
    info = sf.info(str(ref_path))
    rec = Recording(
        user_id=user.id,
        s3_key=s3_key,
        duration_s=float(info.duration),
        sample_rate=int(info.samplerate),
        channels=int(info.channels),
        sha256=sha,
        snr_db=60.0,
        speech_ratio=1.0,
        lufs=-20.0,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _ensure_profile(db: Session, user: User, rec: Recording) -> VoiceProfile:
    p = db.scalar(
        select(VoiceProfile).where(
            VoiceProfile.user_id == user.id,
            VoiceProfile.name == "smoke",
        )
    )
    if p is not None:
        return p
    p = VoiceProfile(
        user_id=user.id,
        name="smoke",
        reference_ids=[rec.id],
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _enqueue(
    db: Session,
    user: User,
    profile: VoiceProfile,
    text: str,
    model: str,
) -> Synthesis:
    syn = Synthesis(
        user_id=user.id,
        profile_id=profile.id,
        model=SynthesisModel(model),
        text=text,
        options={},
        status=SynthesisStatus.queued,
    )
    db.add(syn)
    db.commit()
    db.refresh(syn)

    from app.workers.celery_app import celery_app
    celery_app.send_task(
        "app.workers.tasks.synthesize",
        kwargs={"synthesis_id": str(syn.id), "model": model},
        queue=f"synth.{model}",
    )
    return syn


def _poll(db: Session, syn_id: UUID, timeout_s: float = 600.0) -> Synthesis:
    t0 = time.time()
    last_status = None
    while time.time() - t0 < timeout_s:
        db.expire_all()
        syn = db.get(Synthesis, syn_id)
        if syn is None:
            raise RuntimeError("synthesis row vanished")
        if syn.status != last_status:
            print(f"  [{int(time.time()-t0):3d}s] status={syn.status.value}", flush=True)
            last_status = syn.status
        if syn.status in (SynthesisStatus.succeeded, SynthesisStatus.failed):
            return syn
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"timeout after {timeout_s}s; last status={last_status}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["chatterbox", "omnivoice", "qwen3tts"], required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--ref", required=True, type=Path)
    ap.add_argument("--timeout", type=float, default=600.0)
    args = ap.parse_args()

    if not args.ref.exists():
        print(f"ERR: ref not found: {args.ref}", file=sys.stderr)
        return 2

    print(f"→ model={args.model}  text={args.text!r}  ref={args.ref}", flush=True)
    db = _sync_session()
    try:
        user = _ensure_user(db)
        rec = _ensure_recording(db, user, args.ref)
        profile = _ensure_profile(db, user, rec)
        print(f"  user={user.id}  rec={rec.id}  profile={profile.id}", flush=True)

        syn = _enqueue(db, user, profile, args.text, args.model)
        print(f"  enqueued synthesis_id={syn.id}", flush=True)

        final = _poll(db, syn.id, timeout_s=args.timeout)
        print()
        if final.status == SynthesisStatus.succeeded:
            print("✓ SUCCEEDED")
            print(f"  s3_key_output      = {final.s3_key_output}")
            print(f"  duration_s         = {final.duration_s}")
            print(f"  rtf                = {final.rtf}")
            print(f"  watermark_scheme   = {final.watermark_scheme}")
            print(f"  watermark_verified = {final.watermark_verified}")
            print(f"  aasist_score       = {final.aasist_score}")
            return 0 if final.watermark_verified else 1
        else:
            print("✗ FAILED")
            print(f"  error = {final.error}")
            return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
