from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.profile import ProfileCreateIn, ProfileList, ProfileOut
from app.services import audit_log as audit_svc
from app.services import voice_profiles as profiles_svc

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ProfileCreateIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
) -> ProfileOut:
    try:
        profile = await profiles_svc.create_for_references(
            session,
            user=user,
            name=payload.name,
            reference_ids=payload.reference_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await audit_svc.append(
        session,
        actor_id=user.id,
        action="profile.created",
        resource_type="voice_profile",
        resource_id=str(profile.id),
        payload={
            "name": profile.name,
            "n_references": len(profile.reference_ids),
            "ip": request.client.host if request.client else None,
        },
    )
    await session.commit()
    return ProfileOut.model_validate(profile, from_attributes=True)


@router.get("", response_model=ProfileList)
async def list_mine(user: CurrentUserDep, session: SessionDep) -> ProfileList:
    rows = await profiles_svc.list_for_user(session, user_id=user.id)
    return ProfileList(
        items=[ProfileOut.model_validate(r, from_attributes=True) for r in rows],
        total=len(rows),
    )


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_one(
    profile_id: UUID, user: CurrentUserDep, session: SessionDep
) -> ProfileOut:
    p = await profiles_svc.get_owned(session, user_id=user.id, profile_id=profile_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return ProfileOut.model_validate(p, from_attributes=True)
