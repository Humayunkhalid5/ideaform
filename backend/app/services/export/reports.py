"""Documentation Agent reports (AI_DESIGN 7): feasibility report and business model.

Both are built deterministically from the stored evaluation (no model call, no tokens), so
they can never disagree with what the Evaluation tab shows, and every citation is one the
evidence validation already accepted.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import ProjectArtifact
from app.models.evaluation import DIMENSIONS, Competitor, Evaluation
from app.models.project import Project, ProjectVersion
from app.schemas.evaluation import DIMENSION_LABELS
from app.services.blueprint.agent import next_version_no
from app.services.blueprint.render import _bullets, _cell

REPORT_TYPES = ("feasibility_report", "business_model")
REPORT_TITLES = {"feasibility_report": "Feasibility report", "business_model": "Business model"}

_LABEL = {"verified_fact": "Verified fact", "assumption": "Assumption", "ai_suggestion": "AI suggestion"}


def _band(score: int | None) -> str:
    if score is None:
        return "—"
    return ("Very weak", "Weak", "Mixed", "Good", "Strong")[min(4, max(0, score // 20))]


def feasibility_markdown(project: Project, version: ProjectVersion, evaluation: Evaluation,
                         competitors: list[Competitor]) -> str:
    dims = {d.dimension: d for d in evaluation.dimensions}
    catalogue = {e.get("id"): e for e in (evaluation.evidence or []) if isinstance(e, dict)}
    rows = "\n".join(
        f"| {DIMENSION_LABELS.get(k, k)} | {dims[k].score} | {_band(dims[k].score)} | {dims[k].confidence} |"
        for k in DIMENSIONS if k in dims
    )
    parts = [
        f"# Feasibility report: {project.title}",
        f"_Version {version.version_no} · evaluated {evaluation.created_at:%Y-%m-%d} · "
        f"model {evaluation.model_name or 'unknown'} · prompts {evaluation.prompt_version or 'n/a'}_",
        f"> {evaluation.disclaimer or 'Scores are evidence-based estimates, not predictions of business success.'}",
        "## Summary",
        f"**Overall score: {evaluation.overall_score if evaluation.overall_score is not None else '—'}/100** "
        f"(mean of six dimensions)\n\n{evaluation.summary or ''}",
        "| Dimension | Score | Band | Confidence |\n| --- | --- | --- | --- |\n" + rows,
    ]
    if evaluation.notices:
        parts.append("## Notices\n\n" + _bullets([str(n) for n in evaluation.notices]))

    parts.append("## Dimensions")
    for key in DIMENSIONS:
        d = dims.get(key)
        if d is None:
            continue
        claims = "\n".join(
            f"- **{_LABEL.get(c.get('label'), c.get('label'))}:** {c.get('text')}"
            + (f" ({', '.join(c.get('evidence_ids') or [])})" if c.get("evidence_ids") else "")
            for c in (d.claims or []) if isinstance(c, dict)
        )
        moved = ""
        if d.previous_score is not None:
            moved = f"\n\n**Change from the previous version:** {d.previous_score} → {d.score}. {d.change_reason or ''}"
        parts.append(
            f"### {DIMENSION_LABELS.get(key, key)}: {d.score}/100 ({d.confidence} confidence)\n\n"
            f"{d.explanation}{moved}\n\n"
            + (f"**Claims**\n\n{claims}\n\n" if claims else "")
            + "**Assumptions**\n\n" + _bullets([str(a) for a in d.assumptions or []]) + "\n\n"
            + "**Recommendations**\n\n" + _bullets([str(r) for r in d.recommendations or []])
            + (f"\n\n_Sources: {', '.join(d.evidence_ids)}_" if d.evidence_ids else "")
        )

    risks = [r for r in (evaluation.risks or []) if isinstance(r, dict)]
    if risks:
        table = "\n".join(
            f"| {_cell(r.get('title', ''))} | {r.get('severity', '—')} | {r.get('likelihood', '—')} | {_cell(r.get('mitigation', ''))} |"
            for r in risks
        )
        parts.append("## Risks\n\n| Risk | Severity | Likelihood | Mitigation |\n| --- | --- | --- | --- |\n" + table)
    if evaluation.devils_advocate:
        parts.append("## Devil's Advocate\n\n" + evaluation.devils_advocate)
    critique = evaluation.critique or {}
    if critique.get("must_be_true"):
        parts.append("## What would have to be true\n\n" + _bullets([str(x) for x in critique["must_be_true"]]))
    if critique.get("hidden_assumptions"):
        parts.append("## Hidden assumptions\n\n" + _bullets([str(x) for x in critique["hidden_assumptions"]]))
    improvements = [i for i in (evaluation.improvements or []) if isinstance(i, dict)]
    if improvements:
        parts.append("## Suggested improvements\n\n" + "\n".join(
            f"- **{i.get('title')}**"
            + (f" ({i['decision']})" if i.get("decision") else "")
            + f": {i.get('edited_text') or i.get('change') or i.get('rationale') or ''}"
            for i in improvements
        ))
    if evaluation.alternatives:
        parts.append("## Alternatives\n\n" + _bullets([str(a) for a in evaluation.alternatives]))

    parts.append("## Competitor analysis")
    if competitors:
        parts.append(
            "| Competitor | Target customers | Pricing | Strengths | Weaknesses | Source |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            + "\n".join(
                f"| {_cell(c.name)}{f' ({c.website})' if c.website else ''} | {_cell(c.target_customers or '')} | "
                f"{_cell(c.pricing or '')} | {_cell('; '.join(c.strengths or []))} | "
                f"{_cell('; '.join(c.weaknesses or []))} | {_cell(', '.join(c.evidence_ids or []) or (c.source_url or ''))} |"
                for c in competitors
            )
        )
    else:
        parts.append("_No competitor was named in the retrieved evidence._")

    parts.append("## Sources")
    if catalogue:
        parts.append("\n".join(
            f"- **[{eid}]** {e.get('title') or 'Untitled'}"
            + (f", {e['publisher']}" if e.get("publisher") else "")
            + (f", {e['published_at']}" if e.get("published_at") else "")
            + (f": {e['url']}" if e.get("url") else " (uploaded document)")
            + f" _(KB-{e.get('kb', '?')})_"
            for eid, e in catalogue.items()
        ))
    else:
        parts.append("_No evidence was retrieved; every statement above is an assumption or suggestion._")
    return "\n\n".join(p for p in parts if p).strip() + "\n"


def business_markdown(project: Project, version: ProjectVersion, evaluation: Evaluation) -> str:
    bm = evaluation.business_model or {}
    pricing = [p for p in (bm.get("pricing_options") or []) if isinstance(p, dict)]
    pricing_table = (
        "| Option | Model | Price point | Notes |\n| --- | --- | --- | --- |\n" + "\n".join(
            f"| {_cell(p.get('name', ''))} | {_cell(p.get('model', ''))} | {_cell(str(p.get('price_point') or p.get('price') or ''))} | {_cell(p.get('notes') or p.get('rationale') or '')} |"
            for p in pricing
        )
        if pricing else "_No pricing options were proposed._"
    )
    parts = [
        f"# Business model: {project.title}",
        f"_Version {version.version_no} · from the evaluation of {evaluation.created_at:%Y-%m-%d}_",
    ]
    if not bm:
        parts.append("_The evaluation did not produce a business model. Run the evaluation again._")
    else:
        parts += [
            "## Value proposition\n\n" + (bm.get("value_proposition") or "_Not stated._"),
            "## Customer segments\n\n" + _bullets([str(x) for x in bm.get("customer_segments") or []]),
            "## Channels\n\n" + _bullets([str(x) for x in bm.get("channels") or []]),
            "## Revenue streams\n\n" + _bullets([str(x) for x in bm.get("revenue_streams") or []]),
            "## Cost structure\n\n" + _bullets([str(x) for x in bm.get("cost_structure") or []]),
            "## Pricing options\n\n" + pricing_table,
            "## Key metrics\n\n" + _bullets([str(x) for x in bm.get("key_metrics") or []]),
            "## Assumptions\n\n" + _bullets([str(x) for x in bm.get("assumptions") or []]),
        ]
        if bm.get("evidence_ids"):
            parts.append(f"_Sources: {', '.join(map(str, bm['evidence_ids']))} (see the feasibility report)_")
    return "\n\n".join(parts).strip() + "\n"


def latest_evaluation_for(db: Session, version_id: uuid.UUID) -> Evaluation | None:
    return db.scalar(
        select(Evaluation).where(Evaluation.version_id == version_id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id).limit(1)
    )


def build_reports(db: Session, project: Project, version: ProjectVersion,
                  run_id: uuid.UUID | None = None) -> dict[str, int]:
    """Store a new version of each report whose content changed. Returns type -> version."""
    evaluation = latest_evaluation_for(db, version.id)
    if evaluation is None:
        return {}
    competitors = db.scalars(
        select(Competitor).where(Competitor.evaluation_id == evaluation.id).order_by(Competitor.name)
    ).all()
    contents = {
        "feasibility_report": feasibility_markdown(project, version, evaluation, list(competitors)),
        "business_model": business_markdown(project, version, evaluation),
    }
    made: dict[str, int] = {}
    for artifact_type, content in contents.items():
        latest = db.scalar(
            select(ProjectArtifact).where(ProjectArtifact.version_id == version.id)
            .where(ProjectArtifact.artifact_type == artifact_type)
            .order_by(ProjectArtifact.artifact_version.desc()).limit(1)
        )
        if latest is not None and latest.content == content:
            made[artifact_type] = latest.artifact_version
            continue
        row = ProjectArtifact(
            version_id=version.id,
            artifact_type=artifact_type,
            format="markdown",
            content=content,
            artifact_version=next_version_no(db, version.id, artifact_type),
            edited_by_user=False,
            run_id=run_id,
            data={"evaluation_id": str(evaluation.id), "built_from": "evaluation"},
        )
        db.add(row)
        db.flush()
        made[artifact_type] = row.artifact_version
    db.commit()
    return made
