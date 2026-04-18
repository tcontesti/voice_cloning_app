import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class SynthesisStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SynthesisModel(str, enum.Enum):
    chatterbox = "chatterbox"
    omnivoice = "omnivoice"   # M6
    qwen3tts = "qwen3tts"     # M7
    elevenlabs = "elevenlabs" # M8 — cloud, gated by settings.elevenlabs_enabled


class Synthesis(Base, TimestampedUUIDMixin):
    __tablename__ = "syntheses"
    __table_args__ = {"schema": "app"}

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    profile_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app.voice_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model: Mapped[SynthesisModel] = mapped_column(
        Enum(SynthesisModel, name="synthesis_model", schema="app"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)  # never logged in audit
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[SynthesisStatus] = mapped_column(
        Enum(SynthesisStatus, name="synthesis_status", schema="app"),
        default=SynthesisStatus.queued,
        nullable=False,
        index=True,
    )

    s3_key_output: Mapped[str | None] = mapped_column(String(512), unique=True)
    duration_s: Mapped[float | None] = mapped_column(Float)
    rtf: Mapped[float | None] = mapped_column(Float)
    watermark_scheme: Mapped[str | None] = mapped_column(String(32))
    watermark_verified: Mapped[bool | None] = mapped_column()
    aasist_score: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
