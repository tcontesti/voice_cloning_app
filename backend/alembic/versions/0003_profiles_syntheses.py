"""voice_profiles + syntheses

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE app.profile_status AS ENUM ('pending','ready','failed')")
    op.execute("CREATE TYPE app.synthesis_status AS ENUM ('queued','running','succeeded','failed')")
    op.execute("CREATE TYPE app.synthesis_model AS ENUM ('chatterbox','omnivoice','qwen3tts')")

    op.create_table(
        "voice_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="RESTRICT", name="fk_voice_profiles_user_id_users"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("reference_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("embedding_cache_key", sa.String(128)),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "ready", "failed",
                            name="profile_status", schema="app", create_type=False),
            nullable=False, server_default="ready",
        ),
        schema="app",
    )
    op.create_index("ix_app_voice_profiles_user_id", "voice_profiles", ["user_id"],
                    schema="app", if_not_exists=True)

    op.create_table(
        "syntheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="RESTRICT", name="fk_syntheses_user_id_users"),
            nullable=False,
        ),
        sa.Column(
            "profile_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.voice_profiles.id", ondelete="RESTRICT", name="fk_syntheses_profile_id_voice_profiles"),
            nullable=False,
        ),
        sa.Column(
            "model",
            postgresql.ENUM("chatterbox", "omnivoice", "qwen3tts",
                            name="synthesis_model", schema="app", create_type=False),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("options", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "status",
            postgresql.ENUM("queued", "running", "succeeded", "failed",
                            name="synthesis_status", schema="app", create_type=False),
            nullable=False, server_default="queued",
        ),
        sa.Column("s3_key_output", sa.String(512)),
        sa.Column("duration_s", sa.Float),
        sa.Column("rtf", sa.Float),
        sa.Column("watermark_scheme", sa.String(32)),
        sa.Column("watermark_verified", sa.Boolean),
        sa.Column("aasist_score", sa.Float),
        sa.Column("error", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("s3_key_output", name="uq_syntheses_s3_key_output"),
        schema="app",
    )
    op.create_index("ix_app_syntheses_user_id", "syntheses", ["user_id"],
                    schema="app", if_not_exists=True)
    op.create_index("ix_app_syntheses_status", "syntheses", ["status"],
                    schema="app", if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_app_syntheses_status", table_name="syntheses", schema="app")
    op.drop_index("ix_app_syntheses_user_id", table_name="syntheses", schema="app")
    op.drop_table("syntheses", schema="app")
    op.drop_index("ix_app_voice_profiles_user_id", table_name="voice_profiles", schema="app")
    op.drop_table("voice_profiles", schema="app")
    op.execute("DROP TYPE app.synthesis_model")
    op.execute("DROP TYPE app.synthesis_status")
    op.execute("DROP TYPE app.profile_status")
