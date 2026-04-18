from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.profile import ProfileCreateIn, ProfileList, ProfileOut, ProfileUpdateIn
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


@router.patch("/{profile_id}", response_model=ProfileOut)
async def update(
    profile_id: UUID,
    payload: ProfileUpdateIn,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
) -> ProfileOut:
    profile = await profiles_svc.get_owned(
        session, user_id=user.id, profile_id=profile_id
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    changes: dict[str, object] = {}
    if payload.name is not None and payload.name != profile.name:
        old = profile.name
        await profiles_svc.rename(session, profile=profile, name=payload.name)
        changes["name"] = {"from": old, "to": payload.name}

    if payload.reference_ids is not None:
        try:
            old_refs = list(profile.reference_ids)
            await profiles_svc.set_references(
                session, user=user, profile=profile, reference_ids=payload.reference_ids,
            )
            changes["reference_ids"] = {
                "from_count": len(old_refs),
                "to_count": len(payload.reference_ids),
            }
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    if changes:
        await audit_svc.append(
            session,
            actor_id=user.id,
            action="profile.updated",
            resource_type="voice_profile",
            resource_id=str(profile.id),
            payload={
                **changes,
                "ip": request.client.host if request.client else None,
            },
        )
        await session.commit()
    return ProfileOut.model_validate(profile, from_attributes=True)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one(
    profile_id: UUID,
    request: Request,
    user: CurrentUserDep,
    session: SessionDep,
    cascade: bool = False,
) -> None:
    profile = await profiles_svc.get_owned(
        session, user_id=user.id, profile_id=profile_id
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    snapshot = {
        "name": profile.name,
        "n_references": len(profile.reference_ids),
        "ip": request.client.host if request.client else None,
    }

    if cascade:
        # Caller asked to drop tied syntheses too. n == 0 is fine — the
        # operation is still idempotent and audit-worthy so the log shows
        # intent even when there was nothing to cascade.
        n_syn = await profiles_svc.cascade_delete(session, profile=profile)
        await audit_svc.append(
            session,
            actor_id=user.id,
            action="profile.cascade_deleted",
            resource_type="voice_profile",
            resource_id=str(profile_id),
            payload={**snapshot, "n_syntheses": n_syn},
        )
        await session.commit()
        return

    try:
        await profiles_svc.delete(session, profile=profile)
    except profiles_svc.ProfileInUseError as e:
        # 409 Conflict is the right code when the resource exists but the
        # requested operation is blocked by referential state the caller
        # could in principle resolve. Frontend parses this detail to offer
        # the cascade flow; the "in use by N synthesis row(s)" shape is
        # load-bearing for that parser — update both sides together.
        n_in_use = await profiles_svc.count_syntheses(session, profile_id=profile_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "reason": "in_use",
                "n_syntheses": n_in_use,
            },
        ) from e

    await audit_svc.append(
        session,
        actor_id=user.id,
        action="profile.deleted",
        resource_type="voice_profile",
        resource_id=str(profile_id),
        payload=snapshot,
    )
    await session.commit()
