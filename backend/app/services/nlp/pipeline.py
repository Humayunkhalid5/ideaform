"""Natural language understanding: classification, extraction, persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.agent import AgentRun
from app.models.project import Project, ProjectRequirement, ProjectVersion
from app.services.nlp.extraction import classify_idea, extract_idea, extract_requirements


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _start_run(db: Session, run_id: uuid.UUID | None) -> AgentRun | None:
    run = db.get(AgentRun, run_id) if run_id else None
    if run is not None:
        run.status = "running"
        run.started_at = _utcnow()
        db.commit()
    return run


def _fail_run(
    db: Session,
    project: Project,
    run_id: uuid.UUID | None,
    exc: Exception,
    project_status: str = "failed",
) -> None:
    db.rollback()
    project.status = project_status
    if run_id is not None:
        failed_run = db.get(AgentRun, run_id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.finished_at = _utcnow()
            failed_run.error_message = str(exc)[:2_000]
    db.commit()


def _load(db: Session, project_id: uuid.UUID) -> tuple[Project, ProjectVersion]:
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    version = (
        db.get(ProjectVersion, project.current_version_id)
        if project.current_version_id
        else None
    )
    if version is None:
        raise ValueError("Project has no idea version")
    return project, version


def run_requirements(
    db: Session, project_id: uuid.UUID, run_id: uuid.UUID | None = None
) -> dict:
    """Re-extract requirements for the current version.

    Rows the user edited (``source='user'``) or confirmed are kept; every other
    row is replaced by the fresh extraction.
    """
    project, version = _load(db, project_id)
    # a failed regeneration leaves the earlier extraction intact
    status_on_failure = "ready" if version.structured_idea is not None else "failed"
    run = _start_run(db, run_id)

    try:
        requirements, result = extract_requirements(version.idea_text)

        db.execute(
            delete(ProjectRequirement)
            .where(ProjectRequirement.version_id == version.id)
            .where(ProjectRequirement.confirmed.is_(False))
            .where(func.coalesce(ProjectRequirement.source, "extracted") != "user")
        )
        kept = {
            r.description.strip().lower()
            for r in db.scalars(
                select(ProjectRequirement).where(ProjectRequirement.version_id == version.id)
            )
        }
        added = 0
        for item in requirements:
            if item.description.strip().lower() in kept:
                continue
            db.add(
                ProjectRequirement(
                    version_id=version.id,
                    req_type=item.req_type,
                    description=item.description,
                    priority=item.priority,
                    source=item.source,
                )
            )
            added += 1

        project.status = "ready"
        if run is not None:
            run.status = "succeeded"
            run.finished_at = _utcnow()
            run.model_name = result.model
            run.tokens_in = result.tokens_in
            run.tokens_out = result.tokens_out
            run.output_ref = {"requirements_added": added, "requirements_kept": len(kept)}
        db.commit()
        return {"requirements_added": added, "requirements_kept": len(kept)}

    except Exception as exc:
        _fail_run(db, project, run_id, exc, status_on_failure)
        raise


def run_understanding(
    db: Session, project_id: uuid.UUID, run_id: uuid.UUID | None = None
) -> dict:
    """Fill ``structured_idea`` and requirements for a project's current version."""
    project, version = _load(db, project_id)
    run = _start_run(db, run_id)

    try:
        classification, cls_result = classify_idea(version.idea_text)
        structured, idea_result = extract_idea(version.idea_text, classification.category)
        requirements, req_result = extract_requirements(version.idea_text)

        version.structured_idea = {
            **structured.model_dump(),
            "classification": classification.model_dump(),
        }
        project.category = classification.category

        db.execute(
            delete(ProjectRequirement).where(ProjectRequirement.version_id == version.id)
        )
        for item in requirements:
            db.add(
                ProjectRequirement(
                    version_id=version.id,
                    req_type=item.req_type,
                    description=item.description,
                    priority=item.priority,
                    source=item.source,
                )
            )

        project.status = "ready"
        if run is not None:
            run.status = "succeeded"
            run.finished_at = _utcnow()
            run.model_name = idea_result.model
            run.tokens_in = cls_result.tokens_in + idea_result.tokens_in + req_result.tokens_in
            run.tokens_out = cls_result.tokens_out + idea_result.tokens_out + req_result.tokens_out
            run.output_ref = {
                "category": classification.category,
                "requirements": len(requirements),
            }
        db.commit()
        return {"category": classification.category, "requirements": len(requirements)}

    except Exception as exc:
        _fail_run(db, project, run_id, exc)
        raise
