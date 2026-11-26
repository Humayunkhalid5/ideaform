"""Blueprint generation (Phase 4): Product Design Agent, Technical Architect Agent and the
document generators, with per-section regeneration and versioned storage.

Steps:

1. Make sure the version has a structured idea (runs understanding first if not).
2. Collect inputs: the idea and its requirements, the latest evaluation (optional), and
   KB-B technical references for the architecture, schema and API sections.
3. Generate the requested sections in dependency order (``generators.ORDER``). A section's
   inputs are the newest stored versions of the sections it depends on, so regenerating one
   section redoes nothing else.
4. Store every section as a new ``project_artifacts`` row (``artifact_version`` + 1) with the
   rendered Markdown, the structured data, what it was built on, and the run that made it.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import AgentRun, ProjectArtifact
from app.models.project import Project, ProjectRequirement, ProjectVersion
from app.schemas.blueprint import ARTIFACT_TITLES, BLUEPRINT_TYPES, ArtifactOut
from app.services.blueprint import generators
from app.services.blueprint.generators import Context, Upstream, Usage
from app.services.blueprint.prompts import PROMPT_VERSION
from app.services.evaluation.agent import _understand_first, latest_evaluation
from app.services.knowledge.retrieval import Filters, Scope, search
from app.services.llm import get_llm
from app.services.nlp.pipeline import _fail_run, _load, _start_run

logger = logging.getLogger(__name__)

MAX_REFERENCES = 8
REFS_PER_QUERY = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ stored sections


def latest_artifacts(db: Session, version_id: uuid.UUID) -> dict[str, ProjectArtifact]:
    """The newest row of every blueprint section of a version."""
    rows = db.scalars(
        select(ProjectArtifact)
        .where(ProjectArtifact.version_id == version_id)
        .where(ProjectArtifact.artifact_type.in_(BLUEPRINT_TYPES))
        .order_by(ProjectArtifact.artifact_type, ProjectArtifact.artifact_version.desc())
    ).all()
    latest: dict[str, ProjectArtifact] = {}
    for row in rows:
        latest.setdefault(row.artifact_type, row)
    return latest


def next_version_no(db: Session, version_id: uuid.UUID, artifact_type: str) -> int:
    current = db.scalar(
        select(func.max(ProjectArtifact.artifact_version))
        .where(ProjectArtifact.version_id == version_id)
        .where(ProjectArtifact.artifact_type == artifact_type)
    )
    return (current or 0) + 1


def _upstream(row: ProjectArtifact) -> Upstream:
    return Upstream(
        artifact_type=row.artifact_type,
        version=row.artifact_version,
        data=row.data,
        content=row.content,
        edited=bool(row.edited_by_user),
    )


def artifact_out(row: ProjectArtifact, latest: dict[str, ProjectArtifact] | None = None) -> ArtifactOut:
    stale = []
    if latest:
        for dep, version in ((row.data or {}).get("based_on") or {}).items():
            newer = latest.get(dep)
            if newer is not None and newer.artifact_version > int(version):
                stale.append(dep)
    return ArtifactOut(
        id=row.id,
        artifact_type=row.artifact_type,
        title=ARTIFACT_TITLES.get(row.artifact_type, row.artifact_type),
        format=row.format,
        content=row.content,
        data=row.data,
        artifact_version=row.artifact_version,
        edited_by_user=bool(row.edited_by_user),
        instructions=row.instructions,
        run_id=row.run_id,
        created_at=row.created_at,
        stale_inputs=stale,
    )


def save_edit(db: Session, row: ProjectArtifact, content: str) -> ProjectArtifact:
    """A user edit never overwrites: it becomes the next version of the section."""
    edited = ProjectArtifact(
        version_id=row.version_id,
        artifact_type=row.artifact_type,
        format=row.format,
        content=content,
        artifact_version=next_version_no(db, row.version_id, row.artifact_type),
        edited_by_user=True,
        data=row.data,
        run_id=None,
    )
    db.add(edited)
    db.commit()
    db.refresh(edited)
    return edited


# ------------------------------------------------------------------ inputs


def _requirements(db: Session, version_id: uuid.UUID) -> list[dict]:
    rows = db.scalars(
        select(ProjectRequirement)
        .where(ProjectRequirement.version_id == version_id)
        .order_by(ProjectRequirement.confirmed.desc(), ProjectRequirement.created_at)
    ).all()
    return [
        {"req_type": r.req_type, "priority": r.priority, "description": r.description, "confirmed": r.confirmed}
        for r in rows
    ]


def _evaluation_text(db: Session, version_id: uuid.UUID) -> str | None:
    evaluation = latest_evaluation(db, version_id)
    if evaluation is None:
        return None
    dims = [(d.dimension, d.score, d.confidence) for d in evaluation.dimensions]
    risks = [r for r in ((evaluation.critique or {}).get("risks") or []) if isinstance(r, dict)]
    return generators.evaluation_block(evaluation.overall_score, dims, risks, evaluation.business_model)


def gather_references(db: Session, project: Project, structured: dict | None) -> list[dict]:
    """KB-B (technical) passages for the architect and the schema/API generators."""
    tech = ", ".join((structured or {}).get("technologies_mentioned") or [])
    queries = [
        f"{project.title} {project.category or ''} application architecture technology stack {tech}",
        "web application authentication authorization security best practices OWASP",
        "REST API design conventions pagination errors status codes",
        "PostgreSQL relational database schema design keys indexes",
    ]
    scope = Scope(user_id=project.user_id, project_id=project.id)
    seen: set[uuid.UUID] = set()
    refs: list[dict] = []
    for query in queries:
        try:
            passages = search(db, query, scope=scope, filters=Filters(kbs=["B"]), k=REFS_PER_QUERY)
        except Exception as exc:  # noqa: BLE001 - references are optional
            logger.warning("KB-B search failed (%s); continuing without references", exc)
            return refs
        for p in passages:
            if p.chunk_id in seen or len(refs) >= MAX_REFERENCES:
                continue
            seen.add(p.chunk_id)
            refs.append({"id": f"R{len(refs) + 1}", "title": p.title, "url": p.url, "content": p.content})
    return refs


# ------------------------------------------------------------------ run


def run_blueprint(
    db: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    *,
    types: list[str] | None = None,
    instructions: str | None = None,
    provider=None,
) -> dict:
    project, version = _load(db, project_id)
    run = _start_run(db, run_id)
    started = time.monotonic()
    wanted = [t for t in generators.ORDER if t in (types or generators.ORDER)]
    if not wanted:
        raise ValueError(f"Unknown blueprint section(s): {types}")

    try:
        if version.structured_idea is None:
            _understand_first(db, project, version)
            project, version = _load(db, project_id)
            run = db.get(AgentRun, run_id) if run_id else None
            project.status = "analysing"
            db.commit()

        notices: list[str] = []  # run-level, for the run summary
        evaluation = _evaluation_text(db, version.id)
        no_eval = "This version has not been evaluated, so the blueprint does not use scores or risks."
        no_refs = "No technical references (KB-B) were found; choices rest on general practice."
        if evaluation is None:
            notices.append(no_eval)
        refs = (
            gather_references(db, project, version.structured_idea)
            if set(wanted) & generators.USES_REFERENCES
            else []
        )
        if set(wanted) & generators.USES_REFERENCES and not refs:
            notices.append(no_refs)

        def section_notices(artifact_type: str) -> list[str]:
            """Only the notices that are true for this section's own inputs."""
            out = [no_eval] if no_eval in notices and artifact_type in generators.USES_EVALUATION else []
            if no_refs in notices and artifact_type in generators.USES_REFERENCES:
                out.append(no_refs)
            return out
        reqs = _requirements(db, version.id)
        ctx = Context(
            title=project.title,
            idea=generators.idea_block(project.title, project.category, version.idea_text,
                                       version.structured_idea, reqs),
            evaluation=evaluation,
            references=refs,
            requirements=[
                {"kind": "non_functional" if r["req_type"] == "non_functional" else "functional",
                 "priority": r["priority"] or "should", "text": r["description"]}
                for r in reqs if r["req_type"] in ("functional", "non_functional")
            ],
        )

        usage = Usage()
        made: dict[str, int] = {}
        latest = latest_artifacts(db, version.id)
        for artifact_type in wanted:
            upstream = {t: _upstream(row) for t, row in latest.items()}
            section = generators.generate_section(
                provider or get_llm(),
                artifact_type,
                ctx,
                upstream,
                usage,
                instructions=instructions if len(wanted) == 1 else None,
            )
            row = ProjectArtifact(
                version_id=version.id,
                artifact_type=artifact_type,
                format="markdown",
                content=section.markdown,
                artifact_version=next_version_no(db, version.id, artifact_type),
                edited_by_user=False,
                run_id=run.id if run else None,
                instructions=(instructions or None) if len(wanted) == 1 else None,
                data={
                    **section.data,
                    "based_on": section.based_on,
                    "notices": section_notices(artifact_type),
                    "model": usage.model,
                    "prompt_version": PROMPT_VERSION,
                },
            )
            db.add(row)
            db.commit()  # each finished section is kept even if a later one fails
            latest[artifact_type] = row
            made[artifact_type] = row.artifact_version

        summary = {
            "version_no": version.version_no,
            "sections": made,
            "references": len(refs),
            "notices": notices,
            "llm_calls": usage.calls,
            "seconds": round(time.monotonic() - started, 1),
        }
        project.status = "ready"
        if run is not None:
            run.status = "succeeded"
            run.finished_at = _utcnow()
            run.model_name = usage.model
            run.prompt_version = PROMPT_VERSION
            run.tokens_in = usage.tokens_in
            run.tokens_out = usage.tokens_out
            run.output_ref = summary
        db.commit()
        return summary

    except Exception as exc:
        logger.exception("blueprint failed for %s", project_id)
        _fail_run(db, project, run_id, exc, "ready" if version.structured_idea else "failed")
        raise
