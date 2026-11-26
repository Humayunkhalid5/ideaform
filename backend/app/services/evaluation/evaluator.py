"""The Evaluation Agent's LLM calls, free of database code so they can be tested alone.

One evaluation is four structured calls (each JSON-validated with one repair):

1. dimensions, in two batches of three (strong tier) so each request stays inside
   the free tier's per-request token budget;
2. critique: risks, Devil's Advocate, improvements, alternatives (strong tier);
3. competitors from the competition evidence (fast tier, like the Research Agent);
4. business model (strong tier).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.models.evaluation import DIMENSIONS
from app.schemas.evaluation import (
    DIMENSION_LABELS,
    BusinessModelResult,
    CompetitorItem,
    CompetitorList,
    CritiqueResult,
    DimensionBatch,
    DimensionResult,
    RewrittenIdea,
)
from app.services.evaluation import prompts
from app.services.evaluation.evidence import EvidenceSet, format_block
from app.services.llm import ChatMessage, generate_json
from app.services.llm.base import LLMError, LLMProvider, LLMResult, LLMTier

BATCHES = (
    ("technical_feasibility", "market_opportunity", "competition"),
    ("business_model", "resource_requirements", "execution_complexity"),
)
EVAL_TEMPERATURE = 0.2
CREATIVE_TEMPERATURE = 0.5
REASONING = "low"


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = 0
    model: str | None = None

    def add(self, result: LLMResult) -> None:
        self.tokens_in += result.tokens_in
        self.tokens_out += result.tokens_out
        self.calls += 1
        self.model = self.model or result.model


@dataclass
class Baseline:
    """The previous evaluation the new one is compared against (improvement loop)."""

    version_no: int
    idea_text: str
    dimensions: dict[str, dict]  # dimension -> {score, confidence, explanation}


@dataclass
class EvaluationDraft:
    summary: str
    dimensions: list[DimensionResult]
    critique: CritiqueResult
    competitors: list[CompetitorItem]
    business_model: BusinessModelResult | None
    usage: Usage
    notices: list[str] = field(default_factory=list)


def idea_block(title: str, structured: dict | None, idea_text: str) -> str:
    s = {k: v for k, v in (structured or {}).items() if v and k != "classification"}
    return (
        f"PROJECT: {title}\nIDEA TEXT:\n{idea_text[:3000]}\n\n"
        f"STRUCTURED IDEA (JSON):\n{json.dumps(s, ensure_ascii=False)[:1800]}"
    )


def _baseline_block(baseline: Baseline | None, dims: tuple[str, ...]) -> str:
    if baseline is None:
        return ""
    rows = []
    for d in dims:
        prev = baseline.dimensions.get(d)
        if prev:
            rows.append(
                f"- {d}: {prev['score']} ({prev['confidence']}) - {str(prev['explanation'])[:260]}"
            )
    return (
        f"\n\nPREVIOUS EVALUATION (idea version {baseline.version_no}):\n" + "\n".join(rows)
        + f"\nPREVIOUS IDEA TEXT:\n{baseline.idea_text[:1500]}"
    )


def _call(provider, system: str, user: str, schema, usage: Usage, *, tier, temperature, max_tokens):
    parsed, result = generate_json(
        provider,
        [ChatMessage.system(system), ChatMessage.user(user)],
        schema,
        tier=tier,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=REASONING,
    )
    usage.add(result)
    return parsed


def score_dimensions(
    provider: LLMProvider,
    idea: str,
    evidence: EvidenceSet,
    usage: Usage,
    baseline: Baseline | None = None,
) -> tuple[str, list[DimensionResult]]:
    results: dict[str, DimensionResult] = {}
    summaries: list[str] = []
    for batch in BATCHES:
        wanted = list(batch)
        for _ in range(2):  # one follow-up if the model skipped a dimension
            block = format_block(evidence.subset(wanted))
            parsed: DimensionBatch = _call(
                provider,
                prompts.dimensions_task(wanted, baseline is not None),
                f"{idea}\n\nEVIDENCE:\n{block}{_baseline_block(baseline, tuple(wanted))}",
                DimensionBatch,
                usage,
                tier=LLMTier.STRONG,
                temperature=EVAL_TEMPERATURE,
                max_tokens=3200,
            )
            if parsed.summary:
                summaries.append(parsed.summary.strip())
            for dim in parsed.dimensions:
                if dim.dimension in wanted and dim.dimension not in results:
                    results[dim.dimension] = dim
            wanted = [d for d in wanted if d not in results]
            if not wanted:
                break
        if wanted:
            raise LLMError(f"Evaluation incomplete: no result for {', '.join(wanted)}")
    summary = summaries[-1] if summaries else ""
    return summary, [results[d] for d in DIMENSIONS]


def critique(
    provider: LLMProvider,
    idea: str,
    dimensions: list[DimensionResult],
    evidence: EvidenceSet,
    usage: Usage,
) -> CritiqueResult:
    scores = "\n".join(
        f"- {d.dimension}: {d.score} ({d.confidence}) - {d.explanation[:200]}" for d in dimensions
    )
    weakest = sorted(dimensions, key=lambda d: d.score)[:3]
    block = format_block(
        evidence.subset(["risks", "execution_complexity", "competition", "market_opportunity"])
    )
    return _call(
        provider,
        prompts.CRITIQUE_TASK,
        f"{idea}\n\nDIMENSION SCORES:\n{scores}\nWEAKEST: "
        f"{', '.join(d.dimension for d in weakest)}\n\nEVIDENCE:\n{block}",
        CritiqueResult,
        usage,
        tier=LLMTier.STRONG,
        temperature=CREATIVE_TEMPERATURE,
        max_tokens=3200,
    )


def extract_competitors(
    provider: LLMProvider, idea: str, evidence: EvidenceSet, usage: Usage
) -> list[CompetitorItem]:
    items = evidence.subset(["competition", "market_opportunity", "business_model"])
    if not items:
        return []
    parsed: CompetitorList = _call(
        provider,
        prompts.COMPETITOR_TASK,
        f"{idea}\n\nEVIDENCE:\n{format_block(items, max_chars=600)}",
        CompetitorList,
        usage,
        tier=LLMTier.FAST,
        temperature=0.0,
        max_tokens=2400,
    )
    return parsed.competitors[:6]


def analyse_business(
    provider: LLMProvider, idea: str, evidence: EvidenceSet, usage: Usage
) -> BusinessModelResult:
    block = format_block(evidence.subset(["business_model", "market_opportunity"]))
    return _call(
        provider,
        prompts.BUSINESS_TASK,
        f"{idea}\n\nEVIDENCE:\n{block}",
        BusinessModelResult,
        usage,
        tier=LLMTier.STRONG,
        temperature=EVAL_TEMPERATURE,
        max_tokens=2200,
    )


def evaluate(
    provider: LLMProvider,
    *,
    title: str,
    structured: dict | None,
    idea_text: str,
    evidence: EvidenceSet,
    baseline: Baseline | None = None,
) -> EvaluationDraft:
    """Run every call and return the raw draft; validation and storage happen later."""
    usage = Usage()
    idea = idea_block(title, structured, idea_text)
    summary, dimensions = score_dimensions(provider, idea, evidence, usage, baseline)
    crit = critique(provider, idea, dimensions, evidence, usage)
    notices: list[str] = []
    try:
        competitors = extract_competitors(provider, idea, evidence, usage)
    except LLMError as exc:
        competitors = []
        notices.append(f"Competitor extraction failed and was skipped ({str(exc)[:120]}).")
    try:
        business = analyse_business(provider, idea, evidence, usage)
    except LLMError as exc:
        business = None
        notices.append(f"Business model analysis failed and was skipped ({str(exc)[:120]}).")

    weakest = min(dimensions, key=lambda d: d.score).dimension
    for item in crit.improvements:
        item.dimension_affected = item.dimension_affected or weakest
    return EvaluationDraft(
        summary=summary,
        dimensions=dimensions,
        critique=crit,
        competitors=competitors,
        business_model=business,
        usage=usage,
        notices=notices,
    )


def fallback_change_reason(previous: dict, dim: DimensionResult) -> str:
    """A stated reason when the model gave none (a score change without one is not allowed)."""
    delta = dim.score - int(previous["score"])
    label = DIMENSION_LABELS[dim.dimension]
    first = dim.explanation.split(". ")[0].strip().rstrip(".")
    if delta == 0:
        return f"{label} is unchanged; the assessment still rests on: {first}."
    direction = "rose" if delta > 0 else "fell"
    conf = (
        f" Confidence moved from {previous['confidence']} to {dim.confidence}."
        if previous.get("confidence") != dim.confidence
        else ""
    )
    return f"{label} {direction} by {abs(delta)} points. The new assessment: {first}.{conf}"


def rewrite_idea(
    provider: LLMProvider,
    *,
    title: str,
    idea_text: str,
    changes: list[dict],
    note: str | None,
) -> tuple[RewrittenIdea, LLMResult]:
    lines = [f"- {c.get('title', 'Change')}: {c.get('change') or c.get('title')}" for c in changes]
    if note and note.strip():
        lines.append(f"- The user's own change: {note.strip()}")
    parsed, result = generate_json(
        provider,
        [
            ChatMessage.system(prompts.REWRITE_TASK),
            ChatMessage.user(
                f"PROJECT: {title}\nCURRENT IDEA:\n{idea_text[:4000]}\n\n"
                "ACCEPTED CHANGES:\n" + "\n".join(lines)
            ),
        ],
        RewrittenIdea,
        tier=LLMTier.STRONG,
        temperature=0.3,
        max_tokens=1800,
        reasoning_effort=REASONING,
    )
    return parsed, result
