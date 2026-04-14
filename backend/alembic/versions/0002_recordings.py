"""recordings table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="RESTRICT", name="fk_recordings_user_id_users"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.String(512), nullable=False),
        sa.Column("duration_s", sa.Float, nullable=False),
        sa.Column("sample_rate", sa.Integer, nullable=False),
        sa.Column("channels", sa.Integer, nullable=False, server_default="1"),
        sa.Column("snr_db", sa.Float),
        sa.Column("lufs", sa.Float),
        sa.Column("speech_ratio", sa.Float),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("s3_key", name="uq_recordings_s3_key"),
        schema="app",
    )
    op.create_index("ix_app_recordings_user_id", "recordings", ["user_id"], schema="app")
    op.create_index(
        "ix_app_recordings_user_active",
        "recordings",
        ["user_id", "created_at"],
        schema="app",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_app_recordings_user_active", table_name="recordings", schema="app")
    op.drop_index("ix_app_recordings_user_id", table_name="recordings", schema="app")
    op.drop_table("recordings", schema="app")
