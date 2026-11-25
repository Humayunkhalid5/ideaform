"""Discovery cache and credit usage (Phase 2: Tavily 7-day cache and spend cap).

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_cache",
        sa.Column("cache_key", sa.Text, primary_key=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("results", JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "search_usage",
        sa.Column("day", sa.Date, primary_key=True),
        sa.Column("provider", sa.Text, primary_key=True),
        sa.Column("credits", sa.Integer, nullable=False, server_default="0"),
        sa.Column("requests", sa.Integer, nullable=False, server_default="0"),
    )
    # retrieval filters: published date and source type on sources
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sources_type_date "
        "ON research_sources (source_type, published_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON research_chunks (source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_crawl_job ON crawl_pages (job_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_crawl_job")
    op.execute("DROP INDEX IF EXISTS idx_chunks_source")
    op.execute("DROP INDEX IF EXISTS idx_sources_type_date")
    op.drop_table("search_usage")
    op.drop_table("search_cache")
