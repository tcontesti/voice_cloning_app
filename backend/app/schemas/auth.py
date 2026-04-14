from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.db.models.user import UserRole


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    full_name: str | None = None
