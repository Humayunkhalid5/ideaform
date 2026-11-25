"""Scrape jobs and per-URL crawl log."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKey

JOB_STATUSES = ("queued", "running", "succeeded", "failed", "cancelled")


class ScrapeJob(UUIDPrimaryKey, Base):
    __tablename__ = "scrape_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(repr(s) for s in JOB_STATUSES) + ")",
            name="ck_scrape_jobs_status",
        ),
    )

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL")
    )
    adapter: Mapped[str] = mapped_column(Text, nullable=False)
    seed_urls: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    pages_requested: Mapped[int | None] = mapped_column(Integer)
    pages_fetched: Mapped[int | None] = mapped_column(Integer)
    pages_skipped_robots: Mapped[int | None] = mapped_column(Integer)
    pages_rejected: Mapped[int | None] = mapped_column(Integer)
    token_budget: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    pages = relationship("CrawlPage", back_populates="job", cascade="all, delete-orphan")


class CrawlPage(UUIDPrimaryKey, Base):
    __tablename__ = "crawl_pages"
    __table_args__ = (UniqueConstraint("job_id", "url", name="uq_crawl_job_url"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scrape_jobs.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    robots_allowed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), default=False, nullable=False
    )
    skip_reason: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(Text)
    fetch_ms: Mapped[int | None] = mapped_column(Integer)
    rendered: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), default=False)
    discovery_source: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sources.id", ondelete="SET NULL")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job = relationship("ScrapeJob", back_populates="pages")
