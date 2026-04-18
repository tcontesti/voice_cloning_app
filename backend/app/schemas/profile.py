from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.voice_profile import ProfileStatus


class ProfileCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    reference_ids: list[UUID] = Field(min_length=1, max_length=20)


class ProfileUpdateIn(BaseModel):
    # Partial: send only fields the client wants to change. `reference_ids`
    # is a full replacement of the list (same validation as create).
    name: str | None = Field(default=None, min_length=1, max_length=128)
    reference_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=20)


class ProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    reference_ids: list[UUID]
    status: ProfileStatus
    created_at: datetime


class ProfileList(BaseModel):
    items: list[ProfileOut]
    total: int
