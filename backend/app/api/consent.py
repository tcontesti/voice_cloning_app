from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.consent import ConsentAcceptIn, ConsentOut, ConsentTextOut
from app.services import audit_log as audit_svc
from app.services import consent as consent_svc

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/current", response_model=ConsentTextOut)
async def get_current_text() -> ConsentTextOut:
    text = consent_svc.load_current()
    return ConsentTextOut(
        version=text.version, text_hash=text.text_hash, body_markdown=text.body_markdown
    )


@router.post("/accept", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
async def accept(
    payload: ConsentAcceptIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
) -> ConsentOut:
    current = consent_svc.load_current()
    if payload.version != current.version or payload.text_hash != current.text_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="consent text changed since you read it; reload and re-sign",
        )

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    entry = await consent_svc.record_signature(
        session,
        user=user,
        version=current.version,
        text_hash=current.text_hash,
        ip=ip,
        user_agent=ua,
    )
    await audit_svc.append(
        session,
        actor_id=user.id,
        action="consent.accepted",
        resource_type="consent",
        resource_id=str(entry.id),
        payload={
            "version": current.version,
            "text_hash": current.text_hash,
            "signature_hash": entry.signature_hash,
            "ip": ip,
        },
    )
    await session.commit()
    return ConsentOut.model_validate(entry, from_attributes=True)
