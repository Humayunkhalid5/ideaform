"""Evaluation (Phase 3): evaluate, list evaluations, improvement loop, version comparison.

All endpoints are owner-only (others get 404), like the rest of ``/projects``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.projects import _dispatch, _requirements, _version_or_409, get_owned_project
from app.db.session import get_db
from app.models.evaluation import Evaluation
from app.models.project import Project, ProjectFeedback, ProjectVersion
from app.models.user import User
from app.schemas.evaluation import CompareOut, EvaluationOut, ImproveRequest
from app.services.evaluation.agent import evaluation_out, latest_evaluation
from app.services.evaluation.compare import compare
from app.services.quota import ensure_within_quota

router = APIRouter(prefix="/projects/{project_id}", tags=["evaluation"])


def _version_by_no(db: Session, project: Project, version_no: int) -> ProjectVersion:
    version = db.scalar(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project.id)
        .where(ProjectVersion.version_no == version_no)
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Version {version_no} not found.")
    return version


@router.post("/evaluate", status_code=status.HTTP_202_ACCEPTED)
def evaluate_project(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Run the Evaluation Agent on the current version (understands it first if needed)."""
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    return _dispatch(db, project, version, "evaluation", "evaluate_project")


@router.get("/evaluations", response_model=list[EvaluationOut])
def list_evaluations(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    version: int | None = Query(default=None, ge=1, description="Version number; default current"),
    limit: int = Query(default=5, ge=1, le=50),
) -> list[EvaluationOut]:
    """Evaluations of one version, newest first (the first one is what the UI shows)."""
    target = _version_by_no(db, project, version) if version else _version_or_409(db, project)
    rows = db.scalars(
        select(Evaluation)
        .where(Evaluation.version_id == target.id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id)
        .limit(limit)
    ).all()
    return [evaluation_out(db, e) for e in rows]


@router.post("/improve", status_code=status.HTTP_202_ACCEPTED)
def improve_project(
    payload: ImproveRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Record accept/reject/edit decisions, then build the next version and re-evaluate it."""
    if payload.evaluation_id:
        evaluation = db.get(Evaluation, payload.evaluation_id)
        version = db.get(ProjectVersion, evaluation.version_id) if evaluation else None
        if version is None or version.project_id != project.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Evaluation not found.")
    else:
        version = _version_or_409(db, project)
        evaluation = latest_evaluation(db, version.id)
        if evaluation is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Evaluate this version first.")

    suggestions = {str(i.get("id")): i for i in (evaluation.improvements or []) if isinstance(i, dict)}
    unknown = [d.improvement_id for d in payload.decisions if d.improvement_id not in suggestions]
    if unknown:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Unknown improvement id(s): {', '.join(unknown)}"
        )
    for d in payload.decisions:
        if d.decision == "edited" and not (d.edited_text or "").strip():
            raise HTTPException(422, "An edited suggestion needs edited_text.")

    changes: list[dict] = []
    decided = {d.improvement_id: d for d in payload.decisions}
    updated = []
    for key, item in suggestions.items():
        d = decided.get(key)
        item = dict(item)
        if d is not None:
            item["decision"] = d.decision
            if d.decision == "edited":
                item["edited_text"] = d.edited_text.strip()
            db.add(
                ProjectFeedback(
                    project_id=project.id,
                    version_id=version.id,
                    target_type="improvement",
                    target_id=uuid.UUID(key),
                    decision=d.decision,
                    comment=(d.edited_text or item.get("title") or "")[:4000],
                )
            )
            if d.decision != "rejected":
                changes.append(
                    {
                        "title": item.get("title"),
                        "change": item.get("edited_text") or item.get("change") or item.get("title"),
                        "dimension": item.get("dimension_affected"),
                    }
                )
        updated.append(item)
    evaluation.improvements = updated  # reassign so the JSONB change is saved

    note = (payload.note or "").strip() or None
    if not changes and not note:
        db.commit()  # rejections are still recorded as feedback
        raise HTTPException(
            422, "Accept or edit at least one suggestion, or describe your own change."
        )
    ensure_within_quota(db, current_user)
    db.commit()
    return _dispatch(
        db,
        project,
        version,
        "improvement",
        "improve_project",
        {"evaluation_id": str(evaluation.id), "changes": changes, "note": note},
    )


@router.get("/compare", response_model=CompareOut)
def compare_versions(
    a: int = Query(ge=1, description="Earlier version number"),
    b: int = Query(ge=1, description="Later version number"),
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> CompareOut:
    """Per-dimension score change (with a reason), risks and requirements changed, text diff."""
    version_a, version_b = _version_by_no(db, project, a), _version_by_no(db, project, b)
    eval_a, eval_b = latest_evaluation(db, version_a.id), latest_evaluation(db, version_b.id)
    missing = [str(v.version_no) for v, e in ((version_a, eval_a), (version_b, eval_b)) if e is None]
    if missing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Version(s) {', '.join(missing)} have no evaluation yet."
        )
    result = compare(
        eval_a, eval_b, version_a, version_b, _requirements(db, version_a), _requirements(db, version_b)
    )
    return CompareOut(project_id=project.id, **result)
