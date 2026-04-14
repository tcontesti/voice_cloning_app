from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUserDep, SessionDep
from app.core.security import ACCESS_TOKEN_TTL, create_access_token
from app.schemas.auth import CurrentUser, LoginIn, TokenOut
from app.services import audit_log as audit_svc
from app.services import users as users_svc

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, request: Request, session: SessionDep) -> TokenOut:
    user = await users_svc.authenticate(session, payload.email, payload.password)
    if user is None:
        await audit_svc.append(
            session,
            actor_id=None,
            action="auth.login.failed",
            resource_type="user",
            resource_id=payload.email.lower(),
            payload={"ip": request.client.host if request.client else None},
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    await audit_svc.append(
        session,
        actor_id=user.id,
        action="auth.login.ok",
        resource_type="user",
        resource_id=str(user.id),
        payload={"ip": request.client.host if request.client else None},
    )
    await session.commit()
    return TokenOut(
        access_token=create_access_token(user_id=user.id, email=user.email, role=user.role.value),
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@router.get("/me", response_model=CurrentUser)
async def me(user: CurrentUserDep) -> CurrentUser:
    return CurrentUser(id=user.id, email=user.email, role=user.role, full_name=user.full_name)
