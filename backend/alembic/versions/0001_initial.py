"""initial — users, consents, audit_log

Revision ID: 0001
Revises:
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    op.execute(
        "CREATE TYPE app.user_role AS ENUM ('paciente', 'clinico', 'admin', 'auditor')"
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "paciente", "clinico", "admin", "auditor",
                name="user_role", schema="app", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(255)),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        schema="app",
    )
    op.create_index("ix_app_users_email", "users", ["email"], schema="app")

    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app.users.id", ondelete="RESTRICT", name="fk_consents_user_id_users"),
            nullable=False,
        ),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("signature_hash", sa.String(64), nullable=False),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(512)),
        schema="app",
    )
    op.create_index("ix_app_consents_user_id", "consents", ["user_id"], schema="app")

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128)),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("hash", name="uq_audit_log_hash"),
        schema="audit",
    )
    op.create_index("ix_audit_audit_log_actor_id", "audit_log", ["actor_id"], schema="audit")
    op.create_index("ix_audit_audit_log_action", "audit_log", ["action"], schema="audit")

    # Block UPDATE/DELETE on audit_log via trigger (defense-in-depth; app role
    # also lacks those grants in prod).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.deny_modification() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_log_no_update
            BEFORE UPDATE ON audit.audit_log
            FOR EACH ROW EXECUTE FUNCTION audit.deny_modification();

        CREATE TRIGGER audit_log_no_delete
            BEFORE DELETE ON audit.audit_log
            FOR EACH ROW EXECUTE FUNCTION audit.deny_modification();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_delete ON audit.audit_log")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update ON audit.audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit.deny_modification()")
    op.drop_table("audit_log", schema="audit")
    op.drop_table("consents", schema="app")
    op.drop_table("users", schema="app")
    op.execute("DROP TYPE IF EXISTS app.user_role")
