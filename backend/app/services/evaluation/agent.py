"""Evaluation Agent v1: evidence -> six scored dimensions -> validation -> storage.

Steps (AI_DESIGN 5, 6.2, 6.7):

1. Make sure the version has a structured idea (runs understanding first if not).
2. Gather evidence per dimension with hybrid retrieval over KB-A/B and the project's KB-C.
3. Score six dimensions, critique (risks, Devil's Advocate, improvements, alternatives),
   extract competitors and describe the business model.
4. Validate evidence: unknown ids removed, unsupported facts relabelled as assumptions,
   confidence capped by the number of independent sources.
5. Store ``evaluations``, ``evaluation_dimensions``, ``evaluation_evidence`` and ``competitors``.

When a baseline evaluation is given (or the version's parent has one) the model sees
the previous scores and must state a reason for every score change.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import AgentRun
from app.models.evaluation import (
    DIMENSIONS,
    Competitor,
    Evaluation,
    EvaluationDimension,
    EvaluationEvidence,
)
from app.models.project import Project, ProjectVersion
from app.schemas.evaluation import (
    DIMENSION_LABELS,
    CompetitorItem,
    CompetitorOut,
    DimensionOut,
    EvaluationOut,
    EvidenceRef,
)
from app.services.evaluation import evaluator
from app.services.evaluation.evidence import (
    EvidenceSet,
    gather_evidence,
    validate_dimension,
    validate_ids_on,
)
from app.services.evaluation.prompts import PROMPT_VERSION
from app.services.llm import get_llm
from app.services.nlp.pipeline import _fail_run, _load, _start_run

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Scores are evidence-based estimates from the retrieved sources, not predictions of "
    "business success. Low-confidence scores rest mostly on assumptions."
)
MIN_EVIDENCE = 4
MAX_WEBSITE_LOOKUPS = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def latest_evaluation(db: Session, version_id: uuid.UUID) -> Evaluation | None:
    return db.scalar(
        select(Evaluation)
        .where(Evaluation.version_id == version_id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id)
        .limit(1)
    )


def _baseline(db: Session, evaluation: Evaluation | None) -> evaluator.Baseline | None:
    if evaluation is None:
        return None
    version = db.get(ProjectVersion, evaluation.version_id)
    return evaluator.Baseline(
        version_no=version.version_no if version else 0,
        idea_text=version.idea_text if version else "",
        dimensions={
            d.dimension: {"score": d.score, "confidence": d.confidence, "explanation": d.explanation}
            for d in evaluation.dimensions
        },
    )


# ------------------------------------------------------------------ competitors


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    raw = url if "://" in url else f"https://{url}"
    host = (urlparse(raw).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host or None


def _name_tokens(name: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", name.lower()) if len(t) >= 3]


def verify_website(item: CompetitorItem, evidence: EvidenceSet) -> str | None:
    """Keep a website only if its domain appears in the evidence the model cited."""
    domain = _domain(item.website)
    if not domain:
        return None
    index = evidence.by_id
    cited = [index[r] for r in item.evidence_ids if r in index] or evidence.items
    for ev in cited:
        if domain in (_domain(ev.url) or "") or domain in ev.content.lower():
            return item.website if "://" in item.website else f"https://{item.website}"
    return None


def _lookup_websites(db: Session, items: list[CompetitorItem], category: str | None, search_provider):
    """Tavily discovery for competitors without a verified site (URL discovery only)."""
    if search_provider is None:
        try:
            from app.services.research.discovery import get_search_provider

            search_provider = get_search_provider()
        except Exception:  # noqa: BLE001 - enrichment is optional
            return {}
    found: dict[str, tuple[str, str]] = {}
    for item in [i for i in items if not i.website][:MAX_WEBSITE_LOOKUPS]:
        tokens = _name_tokens(item.name)
        if not tokens:
            continue
        try:
            hits = search_provider.search(
                db, f"{item.name} official website pricing", max_results=5, category=category
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("competitor lookup failed for %s: %s", item.name, exc)
            continue
        for hit in hits:
            host = _domain(hit.url) or ""
            if hit.origin in ("tavily", "cache", "stale-cache") and any(t in host for t in tokens):
                found[item.name] = (f"https://{urlparse(hit.url).hostname}", hit.url)
                break
    return found


# ------------------------------------------------------------------ storage


def evidence_label(dim, ref: str) -> str:
    """Label of the strongest claim citing ``ref``; a passage cited only by the
    explanation supports it directly, so it counts as a verified fact."""
    labels = {c.label for c in dim.claims if ref in c.evidence_ids}
    for label in ("verified_fact", "ai_suggestion", "assumption"):
        if label in labels:
            return label
    return "verified_fact"


def _store(
    db: Session,
    version: ProjectVersion,
    draft: evaluator.EvaluationDraft,
    evidence: EvidenceSet,
    *,
    baseline: Evaluation | None,
    baseline_info: evaluator.Baseline | None,
    run: AgentRun | None,
    notices: list[str],
    websites: dict[str, tuple[str, str]],
) -> Evaluation:
    index = evidence.by_id
    overall = round(sum(d.score for d in draft.dimensions) / len(draft.dimensions))
    crit = draft.critique
    improvements = [
        {
            "id": str(uuid.uuid4()),
            **item.model_dump(),
            "dimension_label": DIMENSION_LABELS.get(item.dimension_affected or "", ""),
            "decision": None,
        }
        for item in crit.improvements
    ]
    risks = [{"id": str(uuid.uuid4()), **r.model_dump()} for r in crit.risks]

    evaluation = Evaluation(
        version_id=version.id,
        summary=draft.summary,
        overall_score=overall,
        risks=risks,
        devils_advocate=crit.devils_advocate,
        critique={
            "hidden_assumptions": crit.hidden_assumptions,
            "must_be_true": crit.must_be_true,
        },
        improvements=improvements,
        alternatives=crit.alternatives,
        business_model=draft.business_model.model_dump() if draft.business_model else None,
        evidence=evidence.catalogue(),
        notices=notices,
        disclaimer=DISCLAIMER,
        baseline_evaluation_id=baseline.id if baseline else None,
        run_id=run.id if run else None,
        model_name=draft.usage.model,
        prompt_version=PROMPT_VERSION,
    )
    db.add(evaluation)
    db.flush()

    for dim in draft.dimensions:
        previous = baseline_info.dimensions.get(dim.dimension) if baseline_info else None
        reason = (dim.change_reason or "").strip() or None
        if previous is not None and not reason:
            reason = evaluator.fallback_change_reason(previous, dim)
        row = EvaluationDimension(
            evaluation_id=evaluation.id,
            dimension=dim.dimension,
            score=dim.score,
            confidence=dim.confidence,
            explanation=dim.explanation or "No explanation returned.",
            assumptions=dim.assumptions[:6],
            recommendations=dim.recommendations[:6],
            claims=[c.model_dump() for c in dim.claims],
            evidence_ids=dim.evidence_ids,
            previous_score=int(previous["score"]) if previous else None,
            change_reason=reason if previous is not None else None,
        )
        db.add(row)
        db.flush()
        linked: set[str] = set()
        for ref in dim.evidence_ids:
            item = index.get(ref)
            if item is None or item.chunk_id in linked:
                continue
            linked.add(item.chunk_id)
            db.add(
                EvaluationEvidence(
                    dimension_id=row.id,
                    chunk_id=uuid.UUID(item.chunk_id),
                    claim_label=evidence_label(dim, ref),
                )
            )

    for item in draft.competitors:
        first = next((index[r] for r in item.evidence_ids if r in index), None)
        website = verify_website(item, evidence)
        source_url = first.url if first else None
        if not website and item.name in websites:
            website, source_url = websites[item.name][0], source_url or websites[item.name][1]
        db.add(
            Competitor(
                version_id=version.id,
                evaluation_id=evaluation.id,
                name=item.name[:200],
                website=website,
                description=item.description,
                target_customers=item.target_customers,
                pricing=item.pricing,
                strengths=item.strengths[:6],
                weaknesses=item.weaknesses[:6],
                differentiation_opportunity=item.differentiation_opportunity,
                source_id=uuid.UUID(first.source_id) if first else None,
                source_url=source_url,
                evidence_ids=item.evidence_ids,
            )
        )
    return evaluation


def run_evaluation(
    db: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    *,
    baseline_evaluation_id: str | uuid.UUID | None = None,
    provider=None,
    search_provider=None,
) -> dict:
    project, version = _load(db, project_id)
    run = _start_run(db, run_id)
    started = time.monotonic()

    try:
        if version.structured_idea is None:
            _understand_first(db, project, version)
            project, version = _load(db, project_id)
            run = db.get(AgentRun, run_id) if run_id else None
            project.status = "analysing"

        baseline = None
        if baseline_evaluation_id:
            baseline = db.get(Evaluation, uuid.UUID(str(baseline_evaluation_id)))
            if baseline is not None:
                base_version = db.get(ProjectVersion, baseline.version_id)
                if base_version is None or base_version.project_id != project.id:
                    baseline = None
        elif version.parent_version_id:
            baseline = latest_evaluation(db, version.parent_version_id)
        baseline_info = _baseline(db, baseline)

        evidence = gather_evidence(
            db,
            title=project.title,
            structured=version.structured_idea,
            idea_text=version.idea_text,
            user_id=project.user_id,
            project_id=project.id,
        )
        draft = evaluator.evaluate(
            provider or get_llm(),
            title=project.title,
            structured=version.structured_idea,
            idea_text=version.idea_text,
            evidence=evidence,
            baseline=baseline_info,
        )

        notices = list(draft.notices)
        if len(evidence.items) < MIN_EVIDENCE:
            notices.insert(
                0,
                "Little evidence was found for this idea, so most scores rest on assumptions. "
                "Run Research or upload documents, then evaluate again.",
            )
        for dim in draft.dimensions:
            notices += validate_dimension(dim, evidence)
        dropped = (
            validate_ids_on(draft.critique.risks, evidence)
            + validate_ids_on(draft.critique.improvements, evidence)
            + validate_ids_on(draft.competitors, evidence)
        )
        if draft.business_model is not None:
            dropped += validate_ids_on([draft.business_model], evidence)
        if dropped:
            notices.append(f"Removed {dropped} citation(s) to evidence that does not exist.")
        draft.competitors = [c for c in draft.competitors if c.evidence_ids]

        websites = _lookup_websites(
            db,
            [c for c in draft.competitors if not verify_website(c, evidence)],
            project.category,
            search_provider,
        )
        evaluation = _store(
            db,
            version,
            draft,
            evidence,
            baseline=baseline,
            baseline_info=baseline_info,
            run=run,
            notices=notices,
            websites=websites,
        )

        summary = {
            "evaluation_id": str(evaluation.id),
            "version_no": version.version_no,
            "overall_score": evaluation.overall_score,
            "scores": {d.dimension: d.score for d in draft.dimensions},
            "evidence": len(evidence.items),
            "competitors": len(draft.competitors),
            "notices": len(notices),
            "baseline_evaluation_id": str(baseline.id) if baseline else None,
            "llm_calls": draft.usage.calls,
            "seconds": round(time.monotonic() - started, 1),
        }
        project.status = "ready"
        if run is not None:
            run.status = "succeeded"
            run.finished_at = _utcnow()
            run.model_name = draft.usage.model
            run.prompt_version = PROMPT_VERSION
            run.tokens_in = draft.usage.tokens_in
            run.tokens_out = draft.usage.tokens_out
            run.output_ref = summary
        db.commit()
        return summary

    except Exception as exc:
        logger.exception("evaluation failed for %s", project_id)
        _fail_run(db, project, run_id, exc, "ready" if version.structured_idea else "failed")
        raise


def _understand_first(db: Session, project: Project, version: ProjectVersion) -> None:
    """Extract the structured idea first; its tokens are recorded on its own run."""
    from app.services.nlp.pipeline import run_understanding

    sub = AgentRun(
        project_id=project.id,
        version_id=version.id,
        agent_name="understanding",
        status="queued",
        input_ref={"version_id": str(version.id), "triggered_by": "evaluation"},
    )
    db.add(sub)
    db.commit()
    run_understanding(db, project.id, sub.id)


# ------------------------------------------------------------------ read model


def evaluation_out(db: Session, evaluation: Evaluation) -> EvaluationOut:
    version = db.get(ProjectVersion, evaluation.version_id)
    catalogue = evaluation.evidence or []
    by_dim = {d.dimension: d for d in evaluation.dimensions}
    dimensions = []
    for key in DIMENSIONS:
        d = by_dim.get(key)
        if d is None:
            continue
        dimensions.append(
            DimensionOut(
                dimension=d.dimension,
                label=DIMENSION_LABELS[d.dimension],
                score=d.score,
                confidence=d.confidence,
                explanation=d.explanation,
                evidence_ids=d.evidence_ids or [],
                claims=d.claims or [],
                assumptions=d.assumptions or [],
                recommendations=d.recommendations or [],
                change_reason=d.change_reason,
                previous_score=d.previous_score,
            )
        )
    competitors = db.scalars(
        select(Competitor).where(Competitor.evaluation_id == evaluation.id).order_by(Competitor.name)
    ).all()
    return EvaluationOut(
        id=evaluation.id,
        version_id=evaluation.version_id,
        version_no=version.version_no if version else 0,
        created_at=evaluation.created_at,
        summary=evaluation.summary,
        overall_score=evaluation.overall_score,
        disclaimer=evaluation.disclaimer,
        dimensions=dimensions,
        risks=evaluation.risks or [],
        devils_advocate=evaluation.devils_advocate,
        critique=evaluation.critique or {},
        improvements=evaluation.improvements or [],
        alternatives=evaluation.alternatives or [],
        business_model=evaluation.business_model,
        competitors=[CompetitorOut.model_validate(c) for c in competitors],
        evidence=[EvidenceRef(**e) for e in catalogue],
        notices=evaluation.notices or [],
        baseline_evaluation_id=evaluation.baseline_evaluation_id,
        run_id=evaluation.run_id,
        model_name=evaluation.model_name,
        prompt_version=evaluation.prompt_version,
    )
