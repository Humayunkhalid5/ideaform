"""Phase 3 schemas: LLM output for the Evaluation Agent and the evaluation API.

LLM-facing models are lenient on purpose (defaults, normalising validators):
the open models served by Groq drift on casing and number types, and a
rejected answer costs a repair call against a tight per-minute token budget.
Evidence and claim rules are enforced afterwards by ``evaluation.evidence``.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.evaluation import DIMENSIONS

Dimension = Literal[
    "technical_feasibility",
    "market_opportunity",
    "competition",
    "business_model",
    "resource_requirements",
    "execution_complexity",
]
ClaimLabel = Literal["verified_fact", "assumption", "ai_suggestion"]
Level = Literal["low", "medium", "high"]

DIMENSION_LABELS: dict[str, str] = {
    "technical_feasibility": "Technical feasibility",
    "market_opportunity": "Market opportunity",
    "competition": "Competition",
    "business_model": "Business model",
    "resource_requirements": "Resource requirements",
    "execution_complexity": "Execution complexity",
}

_EVIDENCE_ID = re.compile(r"E\d{1,3}", re.IGNORECASE)


def normalise_dimension(value: object) -> object:
    """'Technical Feasibility' / 'technical-feasibility' -> 'technical_feasibility'."""
    if not isinstance(value, str):
        return value
    key = re.sub(r"[^a-z]+", "_", value.strip().lower()).strip("_")
    if key in DIMENSIONS:
        return key
    for dim in DIMENSIONS:  # "market" -> market_opportunity, "complexity" -> execution_complexity
        if key and (key in dim or dim.split("_")[0] == key.split("_")[0]):
            return dim
    return key


def normalise_ids(value: object) -> list[str]:
    """Accept ["E1", "[E2]", "e3", 4] or "E1, E2" and return ["E1", "E2", "E3", "E4"]."""
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    out: list[str] = []
    for item in items:
        if isinstance(item, int):
            found = [f"E{item}"]
        else:
            found = [m.upper() for m in _EVIDENCE_ID.findall(str(item))]
        for ref in found:
            if ref not in out:
                out.append(ref)
    return out


def optional_dimension(value: object) -> object:
    """Like ``normalise_dimension`` but unknown names become None instead of failing."""
    key = normalise_dimension(value)
    return key if key in DIMENSIONS else None


def _level(value: object) -> object:
    if isinstance(value, str):
        v = value.strip().lower()
        return {"med": "medium", "moderate": "medium", "critical": "high", "very high": "high"}.get(v, v)
    return value


def _text_list(value: object) -> object:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [
            (item.get("text") or item.get("description") or str(item)) if isinstance(item, dict) else str(item)
            for item in value
            if item not in (None, "")
        ]
    return value


# ------------------------------------------------------------------ LLM output


class Claim(BaseModel):
    text: str
    label: ClaimLabel = "assumption"
    evidence_ids: list[str] = Field(default_factory=list)

    _ids = field_validator("evidence_ids", mode="before")(normalise_ids)

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, v: object) -> object:
        if isinstance(v, str):
            key = re.sub(r"[^a-z]+", "_", v.lower()).strip("_")
            return {
                "fact": "verified_fact",
                "verified": "verified_fact",
                "suggestion": "ai_suggestion",
                "recommendation": "ai_suggestion",
            }.get(key, key)
        return v


class DimensionResult(BaseModel):
    dimension: Dimension
    score: int = Field(ge=0, le=100)
    confidence: Level = "low"
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    change_reason: str | None = None

    _dim = field_validator("dimension", mode="before")(normalise_dimension)
    _ids = field_validator("evidence_ids", mode="before")(normalise_ids)
    _conf = field_validator("confidence", mode="before")(_level)
    _lists = field_validator("assumptions", "recommendations", mode="before")(_text_list)

    @field_validator("score", mode="before")
    @classmethod
    def _score(cls, v: object) -> object:
        try:
            number = float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return v
        if 0 < number <= 10 and not float(number).is_integer():
            number *= 10  # a 0-10 answer like 6.5
        return int(round(max(0.0, min(100.0, number))))


class DimensionBatch(BaseModel):
    summary: str = ""
    dimensions: list[DimensionResult] = Field(default_factory=list)


class Risk(BaseModel):
    title: str
    description: str = ""
    severity: Level = "medium"
    likelihood: Level = "medium"
    mitigation: str = ""
    dimension: Dimension | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    _dim = field_validator("dimension", mode="before")(optional_dimension)
    _ids = field_validator("evidence_ids", mode="before")(normalise_ids)
    _lvl = field_validator("severity", "likelihood", mode="before")(_level)


class Improvement(BaseModel):
    title: str
    rationale: str = ""
    change: str = Field(default="", description="The concrete edit to make to the idea text")
    expected_effect: str = ""
    dimension_affected: Dimension | None = None  # unknown -> filled with the weakest dimension
    evidence_ids: list[str] = Field(default_factory=list)

    _dim = field_validator("dimension_affected", mode="before")(optional_dimension)
    _ids = field_validator("evidence_ids", mode="before")(normalise_ids)


class CritiqueResult(BaseModel):
    risks: list[Risk] = Field(default_factory=list)
    devils_advocate: str = ""
    hidden_assumptions: list[str] = Field(default_factory=list)
    must_be_true: list[str] = Field(default_factory=list)
    improvements: list[Improvement] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)

    _lists = field_validator("hidden_assumptions", "must_be_true", "alternatives", mode="before")(
        _text_list
    )


class CompetitorItem(BaseModel):
    name: str
    website: str | None = None
    description: str | None = None
    target_customers: str | None = None
    pricing: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    differentiation_opportunity: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)

    _ids = field_validator("evidence_ids", mode="before")(normalise_ids)
    _lists = field_validator("strengths", "weaknesses", mode="before")(_text_list)

    @field_validator("target_customers", "pricing", "description", mode="before")
    @classmethod
    def _join(cls, v: object) -> object:
        return ", ".join(str(x) for x in v) if isinstance(v, list) else v


class CompetitorList(BaseModel):
    competitors: list[CompetitorItem] = Field(default_factory=list)


class PricingOption(BaseModel):
    name: str
    model: str = ""
    price_point: str = ""
    rationale: str = ""


class BusinessModelResult(BaseModel):
    customer_segments: list[str] = Field(default_factory=list)
    value_proposition: str = ""
    channels: list[str] = Field(default_factory=list)
    revenue_streams: list[str] = Field(default_factory=list)
    cost_structure: list[str] = Field(default_factory=list)
    pricing_options: list[PricingOption] = Field(default_factory=list)
    key_metrics: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    _ids = field_validator("evidence_ids", mode="before")(normalise_ids)
    _lists = field_validator(
        "customer_segments", "channels", "revenue_streams", "cost_structure", "key_metrics",
        "assumptions", mode="before",
    )(_text_list)


class RewrittenIdea(BaseModel):
    idea_text: str = Field(min_length=20)
    change_summary: str = ""


# ------------------------------------------------------------------ API


class EvidenceRef(BaseModel):
    id: str  # E1, E2 ...
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    kb: str
    title: str | None = None
    url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    snippet: str = ""


class DimensionOut(BaseModel):
    dimension: str
    label: str
    score: int
    confidence: Level
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    change_reason: str | None = None
    previous_score: int | None = None


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    website: str | None = None
    description: str | None = None
    target_customers: str | None = None
    pricing: str | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    differentiation_opportunity: str | None = None
    source_url: str | None = None
    evidence_ids: list[str] | None = None


class EvaluationOut(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    version_no: int
    created_at: datetime
    summary: str | None = None
    overall_score: int | None = None
    disclaimer: str | None = None
    dimensions: list[DimensionOut] = Field(default_factory=list)
    risks: list[dict] = Field(default_factory=list)
    devils_advocate: str | None = None
    critique: dict = Field(default_factory=dict)
    improvements: list[dict] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    business_model: dict | None = None
    competitors: list[CompetitorOut] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    notices: list[str] = Field(default_factory=list)
    baseline_evaluation_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    model_name: str | None = None
    prompt_version: str | None = None


class ImprovementDecision(BaseModel):
    improvement_id: str = Field(min_length=1, max_length=64)
    decision: Literal["accepted", "rejected", "edited"]
    edited_text: str | None = Field(default=None, max_length=4_000)


class ImproveRequest(BaseModel):
    evaluation_id: uuid.UUID | None = None  # default: latest evaluation of the current version
    decisions: list[ImprovementDecision] = Field(default_factory=list, max_length=40)
    note: str | None = Field(default=None, max_length=4_000)  # the user's own extra change


class DimensionDiff(BaseModel):
    dimension: str
    label: str
    score_a: int | None
    score_b: int | None
    delta: int | None
    confidence_a: str | None
    confidence_b: str | None
    reason: str


class TextDiffPart(BaseModel):
    op: Literal["equal", "added", "removed"]
    text: str


class CompareOut(BaseModel):
    project_id: uuid.UUID
    a: int
    b: int
    evaluation_a: uuid.UUID
    evaluation_b: uuid.UUID
    overall_a: int | None
    overall_b: int | None
    overall_delta: int | None
    summary: str
    dimensions: list[DimensionDiff]
    risks_added: list[str]
    risks_removed: list[str]
    requirements_added: list[str]
    requirements_removed: list[str]
    idea_diff: list[TextDiffPart]
    change_summary: str | None = None
