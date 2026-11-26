"""Phase 4 blueprint: structured data and regeneration instructions on artifacts.

``0001`` builds its tables from the current models, so on a fresh database these
columns already exist; every statement is therefore ``IF NOT EXISTS``.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE project_artifacts ADD COLUMN IF NOT EXISTS data JSONB")
    op.execute("ALTER TABLE project_artifacts ADD COLUMN IF NOT EXISTS instructions TEXT")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_artifacts_history "
        "ON project_artifacts (version_id, artifact_type, artifact_version DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_artifacts_history")
    op.execute("ALTER TABLE project_artifacts DROP COLUMN IF EXISTS instructions")
    op.execute("ALTER TABLE project_artifacts DROP COLUMN IF EXISTS data")
