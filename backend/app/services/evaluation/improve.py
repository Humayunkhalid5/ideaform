"""Improvement loop (AI_DESIGN 5.6): accepted changes -> new idea version -> re-evaluate.

1. The API records accept/reject/edit decisions in ``project_feedback``.
2. Here the strong model rewrites the idea with the accepted (or edited) changes.
3. A new version is created on top of the evaluated one and made current.
4. Understanding runs on it; requirements the user confirmed or edited are carried over.
5. The Evaluation Agent re-runs with the previous evaluation as its baseline, so every
   dimension stores the previous score and a stated reason for the change. Research
   is reused: KB-C belongs to the project, not to a version.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import AgentRun
from app.models.evaluation import Evaluation
from app.models.project import Project, ProjectRequirement, ProjectVersion
from app.services.evaluation import evaluator
from app.services.evaluation.agent import run_evaluation
from app.services.llm import get_llm
from app.services.nlp.pipeline import _fail_run, _start_run, run_understanding

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sub_run(db: Session, project: Project, version: ProjectVersion, name: str, **ref) -> AgentRun:
    run = AgentRun(
        project_id=project.id,
        version_id=version.id,
        agent_name=name,
        status="queued",
        input_ref={"version_id": str(version.id), "triggered_by": "improvement", **ref},
    )
    db.add(run)
    db.commit()
    return run


def run_improvement(
    db: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    *,
    evaluation_id: str,
    changes: list[dict],
    note: str | None = None,
    provider=None,
    search_provider=None,
) -> dict:
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    run = _start_run(db, run_id)

    try:
        evaluation = db.get(Evaluation, uuid.UUID(str(evaluation_id)))
        base = db.get(ProjectVersion, evaluation.version_id) if evaluation else None
        if base is None or base.project_id != project.id:
            raise ValueError("Evaluation not found for this project")
        provider = provider or get_llm()

        rewritten, rewrite_result = evaluator.rewrite_idea(
            provider, title=project.title, idea_text=base.idea_text, changes=changes, note=note
        )
        titles = [c.get("title") for c in changes if c.get("title")]
        change_summary = (rewritten.change_summary or "").strip() or (
            "Applied: " + "; ".join(titles) if titles else "Applied the user's change."
        )

        # lock the project row so two concurrent edits cannot pick the same number
        db.execute(select(Project.id).where(Project.id == project.id).with_for_update())
        next_no = (
            db.scalar(
                select(func.max(ProjectVersion.version_no)).where(
                    ProjectVersion.project_id == project.id
                )
            )
            or 0
        ) + 1
        version = ProjectVersion(
            project_id=project.id,
            version_no=next_no,
            idea_text=rewritten.idea_text.strip(),
            change_summary=change_summary[:1000],
            parent_version_id=base.id,
        )
        db.add(version)
        db.flush()
        carried = [
            (r.req_type, r.description, r.priority, r.confirmed)
            for r in base.requirements
            if r.confirmed or r.source == "user"
        ]
        project.current_version_id = version.id
        project.status = "analysing"
        if run is not None:
            run.version_id = version.id
        db.commit()

        understanding = _sub_run(db, project, version, "understanding")
        run_understanding(db, project.id, understanding.id)
        existing = {
            r.description.strip().lower()
            for r in db.scalars(
                select(ProjectRequirement).where(ProjectRequirement.version_id == version.id)
            )
        }
        for req_type, description, priority, confirmed in carried:
            if description.strip().lower() not in existing:
                db.add(
                    ProjectRequirement(
                        version_id=version.id,
                        req_type=req_type,
                        description=description,
                        priority=priority,
                        source="user",
                        confirmed=confirmed,
                    )
                )
        db.commit()

        evaluation_run = _sub_run(
            db, project, version, "evaluation", baseline_evaluation_id=str(evaluation.id)
        )
        result = run_evaluation(
            db,
            project.id,
            evaluation_run.id,
            baseline_evaluation_id=evaluation.id,
            provider=provider,
            search_provider=search_provider,
        )

        output = {
            "version_no": version.version_no,
            "version_id": str(version.id),
            "evaluation_id": result["evaluation_id"],
            "change_summary": change_summary,
            "compare": {"a": base.version_no, "b": version.version_no},
            "changes_applied": len(changes) + (1 if note and note.strip() else 0),
        }
        run = db.get(AgentRun, run_id) if run_id else None
        if run is not None:
            run.status = "succeeded"
            run.finished_at = _utcnow()
            run.model_name = rewrite_result.model
            run.tokens_in = rewrite_result.tokens_in
            run.tokens_out = rewrite_result.tokens_out
            run.output_ref = output
        db.commit()
        return output

    except Exception as exc:
        logger.exception("improvement failed for %s", project_id)
        _fail_run(db, project, run_id, exc, "ready")
        raise
