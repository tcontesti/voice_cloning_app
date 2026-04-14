from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.recording import RecordingList, RecordingOut
from app.services import audio_validation as av
from app.services import recordings as rec_svc

router = APIRouter(prefix="/recordings", tags=["recordings"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB hard cap (60s @ 48k stereo PCM ~11 MB)
ALLOWED_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/x-pn-wav"}


@router.post("", response_model=RecordingOut, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
) -> RecordingOut:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported content_type {file.content_type}; expected WAV",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"file too large: {len(raw)} > {MAX_UPLOAD_BYTES}",
        )

    ip = request.client.host if request.client else None
    try:
        rec = await rec_svc.upload(
            session,
            user=user,
            raw_bytes=raw,
            content_type=file.content_type,
            ip=ip,
        )
    except av.AudioValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    await session.commit()
    return RecordingOut.model_validate(rec, from_attributes=True)


@router.get("", response_model=RecordingList)
async def list_mine(user: CurrentUserDep, session: SessionDep) -> RecordingList:
    rows = await rec_svc.list_for_user(session, user_id=user.id)
    return RecordingList(
        items=[RecordingOut.model_validate(r, from_attributes=True) for r in rows],
        total=len(rows),
    )


@router.get("/{recording_id}", response_model=RecordingOut)
async def get_one(
    recording_id: UUID, user: CurrentUserDep, session: SessionDep
) -> RecordingOut:
    rec = await rec_svc.get_owned(session, user_id=user.id, recording_id=recording_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return RecordingOut.model_validate(rec, from_attributes=True)


@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one(
    recording_id: UUID,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    ip = request.client.host if request.client else None
    rec = await rec_svc.soft_delete(session, user=user, recording_id=recording_id, ip=ip)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await session.commit()
