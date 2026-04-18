from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUserDep, SessionDep
from app.core.config import get_settings
from app.db.models.synthesis import SynthesisStatus
from app.schemas.synthesis import (
    ModelInfo,
    SynthesisCreateIn,
    SynthesisList,
    SynthesisOut,
)
from app.services import audit_log as audit_svc
from app.services import storage
from app.services import synthesis as syn_svc
from app.services import voice_profiles as profiles_svc

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


@router.get("/models", response_model=list[ModelInfo])
async def models() -> list[ModelInfo]:
    s = get_settings()
    out = [
        ModelInfo(name="chatterbox", license="MIT", available=True,
                  notes="default · PerTh nativo"),
        ModelInfo(name="omnivoice", license="Apache-2.0", available=True,
                  notes="mejor similitud · AudioSeal post-hoc"),
        ModelInfo(name="qwen3tts", license="Apache-2.0", available=True,
                  notes="venv aislado · subprocess · AudioSeal post-hoc"),
    ]
    if s.elevenlabs_enabled:
        out.append(
            ModelInfo(
                name="elevenlabs",
                license="Proprietary · cloud",
                available=bool(s.elevenlabs_api_key),
                notes="cloud · multi-idioma · datos salen del hospital",
            )
        )
    return out


@router.post("", response_model=SynthesisOut, status_code=status.HTTP_201_CREATED)
async def create(
    payload: SynthesisCreateIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
) -> SynthesisOut:
    profile = await profiles_svc.get_owned(
        session, user_id=user.id, profile_id=payload.profile_id
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    try:
        syn = await syn_svc.create_job(
            session,
            user=user,
            profile_id=payload.profile_id,
            model=payload.model,
            text=payload.text,
            options=payload.options,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Audit BEFORE enqueue so we never lose track of intent.
    await audit_svc.append(
        session,
        actor_id=user.id,
        action="synthesis.queued",
        resource_type="synthesis",
        resource_id=str(syn.id),
        payload={
            "model": payload.model.value,
            "text_len": len(payload.text),
            "ip": request.client.host if request.client else None,
        },
    )
    await session.commit()

    # Enqueue to Celery — done after commit so the worker never reads a row
    # that doesn't exist yet.
    from app.workers.celery_app import celery_app
    celery_app.send_task(
        "app.workers.tasks.synthesize",
        kwargs={"synthesis_id": str(syn.id), "model": payload.model.value},
        queue=f"synth.{payload.model.value}",
    )

    return SynthesisOut.model_validate(syn, from_attributes=True)


@router.get("", response_model=SynthesisList)
async def list_mine(user: CurrentUserDep, session: SessionDep) -> SynthesisList:
    rows = await syn_svc.list_for_user(session, user_id=user.id)
    return SynthesisList(
        items=[SynthesisOut.model_validate(r, from_attributes=True) for r in rows],
        total=len(rows),
    )


@router.get("/{synthesis_id}", response_model=SynthesisOut)
async def get_one(
    synthesis_id: UUID, user: CurrentUserDep, session: SessionDep
) -> SynthesisOut:
    syn = await syn_svc.get_owned(session, user_id=user.id, synthesis_id=synthesis_id)
    if syn is None:
        raise HTTPException(status_code=404, detail="not found")
    return SynthesisOut.model_validate(syn, from_attributes=True)


@router.get("/{synthesis_id}/audio")
async def download_audio(
    synthesis_id: UUID, user: CurrentUserDep, session: SessionDep
) -> Response:
    syn = await syn_svc.get_owned(session, user_id=user.id, synthesis_id=synthesis_id)
    if syn is None or syn.status != SynthesisStatus.succeeded or not syn.s3_key_output:
        raise HTTPException(status_code=404, detail="audio not available")
    bucket = get_settings().minio_bucket_syntheses
    data = storage.get_object(bucket=bucket, key=syn.s3_key_output)
    return StreamingResponse(
        iter([data]),
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="synthesis-{syn.id.hex[:8]}.wav"',
            "Content-Length": str(len(data)),
        },
    )
