"""Initial schema: users, projects, research, evaluations, artifacts, scraper.

The DDL is emitted from ``Base.metadata`` so it can never drift from the models.
Later revisions should be produced with ``alembic revision --autogenerate``.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Indexes that need expressions SQLAlchemy cannot infer from the model columns.
EXTRA_DDL = (
    "CREATE INDEX IF NOT EXISTS idx_sources_kb_category ON research_sources (kb, category)",
    "CREATE INDEX IF NOT EXISTS idx_sources_kb ON research_sources (kb)",
    "CREATE INDEX IF NOT EXISTS idx_sources_project ON research_sources (project_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_hash_scope "
    "ON research_sources (content_hash, COALESCE(project_id, '00000000-0000-0000-0000-000000000000'))",
    "CREATE INDEX IF NOT EXISTS idx_chunks_tsv ON research_chunks USING GIN (tsv)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_scope ON research_chunks (kb, project_id, user_id)",
    "CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops)",
    "CREATE INDEX IF NOT EXISTS idx_runs_project ON agent_runs (project_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_version ON project_artifacts (version_id, artifact_type)",
    "CREATE INDEX IF NOT EXISTS idx_scrape_jobs_project ON scrape_jobs (project_id)",
    "CREATE INDEX IF NOT EXISTS idx_crawl_domain ON crawl_pages (domain, fetched_at)",
    "CREATE INDEX IF NOT EXISTS idx_crawl_hash ON crawl_pages (content_hash)",
    "CREATE INDEX IF NOT EXISTS idx_crawl_discovery ON crawl_pages (discovery_source)",
)


def upgrade() -> None:
    from app.db.base import Base
    import app.models  # noqa: F401 - registers every table on the metadata

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    Base.metadata.create_all(bind=op.get_bind())

    for statement in EXTRA_DDL:
        op.execute(statement)


def downgrade() -> None:
    from app.db.base import Base
    import app.models  # noqa: F401

    Base.metadata.drop_all(bind=op.get_bind())
