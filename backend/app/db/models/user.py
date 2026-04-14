import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedUUIDMixin


class UserRole(str, enum.Enum):
    paciente = "paciente"
    clinico = "clinico"
    admin = "admin"
    auditor = "auditor"


class User(Base, TimestampedUUIDMixin):
    __tablename__ = "users"
    __table_args__ = {"schema": "app"}

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", schema="app"), nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
