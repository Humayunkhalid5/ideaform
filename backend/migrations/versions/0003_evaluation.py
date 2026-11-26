"""Phase 3 evaluation: claims, evidence catalogue, critique, comparison fields.

``0001`` builds its tables from the current models, so on a fresh database these
columns already exist; every statement is therefore ``IF NOT EXISTS``.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

COLUMNS = {
    "evaluations": (
        "overall_score INTEGER",
        "critique JSONB",
        "alternatives JSONB",
        "business_model JSONB",
        "evidence JSONB",
        "notices JSONB",
        "baseline_evaluation_id UUID REFERENCES evaluations (id) ON DELETE SET NULL",
        "model_name TEXT",
        "prompt_version TEXT",
    ),
    "evaluation_dimensions": (
        "claims JSONB",
        "evidence_ids JSONB",
        "previous_score INTEGER",
        "change_reason TEXT",
    ),
    "competitors": (
        "evaluation_id UUID REFERENCES evaluations (id) ON DELETE CASCADE",
        "source_url TEXT",
        "evidence_ids JSONB",
    ),
}

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_evaluations_version ON evaluations (version_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_competitors_evaluation ON competitors (evaluation_id)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_project ON project_feedback (project_id, target_type)",
)


def upgrade() -> None:
    for table, columns in COLUMNS.items():
        for column in columns:
            op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column}")
    for ddl in INDEXES:
        op.execute(ddl)


def downgrade() -> None:
    for ddl in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {ddl.split('EXISTS ')[1].split(' ')[0]}")
    for table, columns in COLUMNS.items():
        for column in columns:
            op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column.split(' ')[0]}")
