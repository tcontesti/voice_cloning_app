import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class ProfileStatus(str, enum.Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class VoiceProfile(Base, TimestampedUUIDMixin):
    """A patient's voice profile = ordered list of reference recordings.

    No model embedding is stored here in M5 — Chatterbox does zero-shot from
    the reference WAV directly each synthesis. M6+ may pre-extract embeddings
    and cache them in Redis under `embedding_cache_key`.
    """

    __tablename__ = "voice_profiles"
    __table_args__ = {"schema": "app"}

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=False
    )
    embedding_cache_key: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus, name="profile_status", schema="app"),
        default=ProfileStatus.ready,
        nullable=False,
    )
