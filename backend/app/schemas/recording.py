from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RecordingOut(BaseModel):
    id: UUID
    user_id: UUID
    duration_s: float
    sample_rate: int
    channels: int
    snr_db: float | None
    lufs: float | None
    speech_ratio: float | None
    sha256: str
    created_at: datetime
    deleted_at: datetime | None = None


class RecordingList(BaseModel):
    items: list[RecordingOut]
    total: int
