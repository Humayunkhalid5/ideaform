"""Projects, idea versions, requirements, and feedback."""

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
from app.models.mixins import Timestamps, UUIDPrimaryKey

CATEGORIES = ("business", "software", "technology")
HELP_LEVELS = ("evaluate", "research", "blueprint", "everything")
PROJECT_STATUSES = ("draft", "analysing", "ready", "failed", "archived")
REQ_TYPES = ("functional", "non_functional", "constraint", "assumption")
PRIORITIES = ("must", "should", "could")
REQ_SOURCES = ("extracted", "user", "ai_suggestion")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Project(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(_in("category", CATEGORIES), name="ck_projects_category"),
        CheckConstraint(_in("help_level", HELP_LEVELS), name="ck_projects_help_level"),
        CheckConstraint(_in("status", PROJECT_STATUSES), name="ck_projects_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    help_level: Mapped[str] = mapped_column(Text, nullable=False, default="everything")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "project_versions.id",
            use_alter=True,
            name="fk_current_version",
            ondelete="SET NULL",
        ),
    )

    user = relationship("User", back_populates="projects")
    versions = relationship(
        "ProjectVersion",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="ProjectVersion.project_id",
        order_by="ProjectVersion.version_no",
    )


class ProjectVersion(UUIDPrimaryKey, Base):
    __tablename__ = "project_versions"
    __table_args__ = (UniqueConstraint("project_id", "version_no", name="uq_version_number"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    idea_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_idea: Mapped[dict | None] = mapped_column(JSONB)
    change_summary: Mapped[str | None] = mapped_column(Text)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project = relationship(
        "Project", back_populates="versions", foreign_keys=[project_id]
    )
    requirements = relationship(
        "ProjectRequirement",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="ProjectRequirement.created_at",
    )


class ProjectRequirement(UUIDPrimaryKey, Base):
    __tablename__ = "project_requirements"
    __table_args__ = (
        CheckConstraint(_in("req_type", REQ_TYPES), name="ck_requirements_type"),
        CheckConstraint(
            "priority IS NULL OR " + _in("priority", PRIORITIES), name="ck_requirements_priority"
        ),
        CheckConstraint(
            "source IS NULL OR " + _in("source", REQ_SOURCES), name="ck_requirements_source"
        ),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False
    )
    req_type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version = relationship("ProjectVersion", back_populates="requirements")


class ProjectFeedback(UUIDPrimaryKey, Base):
    __tablename__ = "project_feedback"
    __table_args__ = (
        CheckConstraint(
            "decision IS NULL OR decision IN ('accepted','rejected','edited')",
            name="ck_feedback_decision",
        ),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_feedback_rating"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE")
    )
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decision: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
