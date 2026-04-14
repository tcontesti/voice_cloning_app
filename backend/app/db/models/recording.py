from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class Recording(Base, TimestampedUUIDMixin):
    __tablename__ = "recordings"
    __table_args__ = {"schema": "app"}

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    duration_s: Mapped[float] = mapped_column(Float, nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    channels: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snr_db: Mapped[float | None] = mapped_column(Float)
    lufs: Mapped[float | None] = mapped_column(Float)
    speech_ratio: Mapped[float | None] = mapped_column(Float)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
