"""synthesis_model: add 'elevenlabs' enum value

The multihost environment already had this label added manually by an
earlier ad-hoc ALTER TYPE; rows in app.syntheses with model='elevenlabs'
exist in the wild. Formalising so fresh installs don't desync with the
Python SynthesisModel enum.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ADD VALUE IF NOT EXISTS is non-transactional but safe and idempotent;
    # running against the multihost DB is a no-op because the label is
    # already present.
    op.execute(
        "ALTER TYPE app.synthesis_model ADD VALUE IF NOT EXISTS 'elevenlabs'"
    )


def downgrade() -> None:
    # Postgres has no ALTER TYPE ... DROP VALUE. Removing an enum label
    # safely would require rewriting the column, so the downgrade is a
    # no-op. Anyone genuinely rolling back past 0004 needs to handle the
    # rows manually.
    pass
