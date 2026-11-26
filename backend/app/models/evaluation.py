"""Evaluations with their six scored dimensions, evidence and competitors."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
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

DIMENSIONS = (
    "technical_feasibility",
    "market_opportunity",
    "competition",
    "business_model",
    "resource_requirements",
    "execution_complexity",
)
CLAIM_LABELS = ("verified_fact", "assumption", "ai_suggestion")


class Evaluation(UUIDPrimaryKey, Base):
    __tablename__ = "evaluations"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    risks: Mapped[list | None] = mapped_column(JSONB)
    devils_advocate: Mapped[str | None] = mapped_column(Text)
    improvements: Mapped[list | None] = mapped_column(JSONB)
    disclaimer: Mapped[str | None] = mapped_column(
        Text,
        server_default=text(
            "'Scores are estimates based on retrieved evidence, not predictions of success.'"
        ),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # Phase 3 (migration 0003)
    overall_score: Mapped[int | None] = mapped_column(Integer)
    critique: Mapped[dict | None] = mapped_column(JSONB)  # hidden assumptions, must be true
    alternatives: Mapped[list | None] = mapped_column(JSONB)
    business_model: Mapped[dict | None] = mapped_column(JSONB)
    # numbered evidence catalogue the model saw: [{id: "E1", chunk_id, source_id, url, ...}]
    evidence: Mapped[list | None] = mapped_column(JSONB)
    notices: Mapped[list | None] = mapped_column(JSONB)  # validation and low-evidence notes
    baseline_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="SET NULL")
    )
    model_name: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dimensions = relationship(
        "EvaluationDimension",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationDimension.dimension",
    )


class EvaluationDimension(UUIDPrimaryKey, Base):
    __tablename__ = "evaluation_dimensions"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ("
            + ", ".join(repr(d) for d in DIMENSIONS)
            + ")",
            name="ck_dimension_name",
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_dimension_score"),
        CheckConstraint(
            "confidence IN ('low','medium','high')", name="ck_dimension_confidence"
        ),
        UniqueConstraint("evaluation_id", "dimension", name="uq_evaluation_dimension"),
    )

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list | None] = mapped_column(JSONB)
    recommendations: Mapped[list | None] = mapped_column(JSONB)
    # Phase 3 (migration 0003)
    claims: Mapped[list | None] = mapped_column(JSONB)  # [{text, label, evidence_ids}]
    evidence_ids: Mapped[list | None] = mapped_column(JSONB)  # ["E1", "E4"]
    previous_score: Mapped[int | None] = mapped_column(Integer)
    change_reason: Mapped[str | None] = mapped_column(Text)

    evaluation = relationship("Evaluation", back_populates="dimensions")
    evidence = relationship(
        "EvaluationEvidence", back_populates="dimension", cascade="all, delete-orphan"
    )


class EvaluationEvidence(Base):
    __tablename__ = "evaluation_evidence"
    __table_args__ = (
        CheckConstraint(
            "claim_label IN (" + ", ".join(repr(c) for c in CLAIM_LABELS) + ")",
            name="ck_evidence_claim",
        ),
    )

    dimension_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_dimensions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    claim_label: Mapped[str] = mapped_column(Text, nullable=False)

    dimension = relationship("EvaluationDimension", back_populates="evidence")


class Competitor(UUIDPrimaryKey, Base):
    __tablename__ = "competitors"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    target_customers: Mapped[str | None] = mapped_column(Text)
    pricing: Mapped[str | None] = mapped_column(Text)
    strengths: Mapped[list | None] = mapped_column(JSONB)
    weaknesses: Mapped[list | None] = mapped_column(JSONB)
    differentiation_opportunity: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_sources.id", ondelete="SET NULL")
    )
    # Phase 3 (migration 0003)
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluations.id", ondelete="CASCADE")
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    evidence_ids: Mapped[list | None] = mapped_column(JSONB)
