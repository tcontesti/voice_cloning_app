from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.synthesis import SynthesisModel, SynthesisStatus


class SynthesisCreateIn(BaseModel):
    profile_id: UUID
    model: SynthesisModel = SynthesisModel.chatterbox
    text: str = Field(min_length=1, max_length=500)
    options: dict | None = None


class SynthesisOut(BaseModel):
    id: UUID
    user_id: UUID
    profile_id: UUID
    model: SynthesisModel
    text: str
    status: SynthesisStatus
    duration_s: float | None
    rtf: float | None
    watermark_scheme: str | None
    watermark_verified: bool | None
    aasist_score: float | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SynthesisList(BaseModel):
    items: list[SynthesisOut]
    total: int


class ModelInfo(BaseModel):
    name: str
    license: str
    available: bool
    notes: str | None = None
