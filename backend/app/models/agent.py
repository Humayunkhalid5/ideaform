"""Agent runs and generated artifacts."""

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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKey

RUN_STATUSES = ("queued", "running", "succeeded", "failed", "retrying")
ARTIFACT_TYPES = (
    "prd",
    "architecture",
    "database_schema",
    "api_spec",
    "ui_ux",
    "business_model",
    "roadmap",
    "feasibility_report",
    "diagram",
)
ARTIFACT_FORMATS = ("markdown", "mermaid", "json", "pdf")


class AgentRun(UUIDPrimaryKey, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN (" + ", ".join(repr(s) for s in RUN_STATUSES) + ")",
            name="ck_runs_status",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE")
    )
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    input_ref: Mapped[dict | None] = mapped_column(JSONB)
    output_ref: Mapped[dict | None] = mapped_column(JSONB)
    model_name: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectArtifact(UUIDPrimaryKey, Base):
    __tablename__ = "project_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN (" + ", ".join(repr(a) for a in ARTIFACT_TYPES) + ")",
            name="ck_artifacts_type",
        ),
        CheckConstraint(
            "format IN (" + ", ".join(repr(f) for f in ARTIFACT_FORMATS) + ")",
            name="ck_artifacts_format",
        ),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False
    )
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    edited_by_user: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), default=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
