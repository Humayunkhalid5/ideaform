"""Phase 5 orchestration: parent run link and the content-hash LLM cache.

``0001`` builds its tables from the current models, so on a fresh database these
already exist; every statement is therefore ``IF NOT EXISTS``.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS parent_run_id UUID "
        "REFERENCES agent_runs (id) ON DELETE CASCADE"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_runs_parent_run_id ON agent_runs (parent_run_id)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_cache (
            cache_key  TEXT PRIMARY KEY,
            model      TEXT,
            response   TEXT NOT NULL,
            tokens_in  INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            hits       INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_cache")
    op.execute("DROP INDEX IF EXISTS ix_agent_runs_parent_run_id")
    op.execute("ALTER TABLE agent_runs DROP COLUMN IF EXISTS parent_run_id")
