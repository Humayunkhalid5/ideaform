"""Phase 5: full analysis, reports, version history and export (architecture.md 8).

All endpoints are owner-only (others get 404), like the rest of ``/projects``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.evaluation import _version_by_no
from app.api.projects import _version_or_409, get_owned_project
from app.api.runs import run_dict
from app.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.agent import AgentRun, ProjectArtifact
from app.models.evaluation import Evaluation
from app.models.project import Project, ProjectVersion
from app.models.user import User
from app.schemas.blueprint import ARTIFACT_TITLES
from app.services.blueprint.agent import artifact_out
from app.services.export.reports import REPORT_TITLES, REPORT_TYPES, build_reports
from app.services.quota import ensure_within_quota

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}", tags=["orchestration"])

HelpLevel = Literal["evaluate", "research", "blueprint", "everything"]
ExportFormat = Literal["pdf", "md", "docx", "zip"]
STALE_AFTER = timedelta(hours=2)  # an "active" analysis older than this is treated as dead


class AnalyseRequest(BaseModel):
    depth: HelpLevel | None = None


def _run_in_background(project_id: str, run_id: str, depth: str | None) -> None:
    from app.services.orchestrator.graph import run_analysis

    db = SessionLocal()
    try:
        run_analysis(db, uuid.UUID(project_id), uuid.UUID(run_id), depth=depth)
    except Exception:  # noqa: BLE001 - the run row records the failure
        logger.exception("background analysis failed for %s", project_id)
    finally:
        db.close()


@router.post("/analyse", status_code=status.HTTP_202_ACCEPTED)
def analyse_project(
    background: BackgroundTasks,
    payload: AnalyseRequest | None = None,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run the whole pipeline (understanding -> research -> evaluation -> business ->
    product design -> technical architecture -> documentation) in the background."""
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    active = db.scalar(
        select(AgentRun).where(AgentRun.project_id == project.id, AgentRun.agent_name == "analysis",
                               AgentRun.status.in_(("queued", "running")))
        .order_by(AgentRun.started_at.desc().nulls_first()).limit(1)
    )
    if active is not None:
        started = active.started_at or datetime.now(timezone.utc)
        if datetime.now(timezone.utc) - started < STALE_AFTER:
            raise HTTPException(status.HTTP_409_CONFLICT, f"An analysis is already running (run {active.id}).")
        active.status, active.error_message = "failed", "abandoned (no progress for 2 hours)"

    depth = (payload.depth if payload else None) or project.help_level or "everything"
    run = AgentRun(project_id=project.id, version_id=version.id, agent_name="analysis", status="queued",
                   input_ref={"version_id": str(version.id), "depth": depth})
    db.add(run)
    project.status = "analysing"
    db.commit()

    if not get_settings().jobs_inline:
        try:
            from app.worker import tasks

            tasks.analyse_project.delay(str(project.id), str(run.id), depth)
            return {"run_id": str(run.id), "status": "queued", "depth": depth}
        except Exception:  # broker unavailable: fall back to a background task here
            logger.warning("celery unavailable, running the analysis in-process for %s", project.id)
    background.add_task(_run_in_background, str(project.id), str(run.id), depth)
    return {"run_id": str(run.id), "status": "queued", "depth": depth}


# ------------------------------------------------------------------ documents (reports)


def _reports(db: Session, version: ProjectVersion) -> list:
    rows = db.scalars(
        select(ProjectArtifact).where(ProjectArtifact.version_id == version.id)
        .where(ProjectArtifact.artifact_type.in_(REPORT_TYPES))
        .order_by(ProjectArtifact.artifact_type, ProjectArtifact.artifact_version.desc())
    ).all()
    latest: dict[str, ProjectArtifact] = {}
    for row in rows:
        latest.setdefault(row.artifact_type, row)
    out = []
    for t in REPORT_TYPES:
        if t in latest:
            item = artifact_out(latest[t]).model_dump()
            item["title"] = REPORT_TITLES[t]
            out.append(item)
    return out


@router.get("/reports")
def list_reports(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    version: int | None = Query(default=None, ge=1),
) -> dict:
    """The Documentation Agent's feasibility report and business model for a version."""
    target = _version_by_no(db, project, version) if version else _version_or_409(db, project)
    evaluated = db.scalar(select(Evaluation.id).where(Evaluation.version_id == target.id).limit(1)) is not None
    return {"version_no": target.version_no, "has_evaluation": evaluated, "reports": _reports(db, target)}


@router.post("/reports", status_code=status.HTTP_201_CREATED)
def rebuild_reports(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> dict:
    """Rebuild the reports from the latest evaluation (no model call, no tokens)."""
    version = _version_or_409(db, project)
    made = build_reports(db, project, version)
    if not made:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evaluate this version first.")
    return {"version_no": version.version_no, "has_evaluation": True, "reports": _reports(db, version)}


# ------------------------------------------------------------------ version history


@router.get("/history")
def project_history(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    runs: int = Query(default=30, ge=1, le=100),
) -> dict:
    """Idea versions with their evaluations and every artifact version, plus recent runs."""
    versions = db.scalars(
        select(ProjectVersion).where(ProjectVersion.project_id == project.id).order_by(ProjectVersion.version_no.desc())
    ).all()
    out_versions = []
    for v in versions:
        evaluations = db.scalars(
            select(Evaluation).where(Evaluation.version_id == v.id).order_by(Evaluation.created_at.desc())
        ).all()
        artifacts = db.scalars(
            select(ProjectArtifact).where(ProjectArtifact.version_id == v.id)
            .order_by(ProjectArtifact.artifact_type, ProjectArtifact.artifact_version.desc())
        ).all()
        grouped: dict[str, list] = {}
        for a in artifacts:
            grouped.setdefault(a.artifact_type, []).append({
                "id": str(a.id), "artifact_version": a.artifact_version, "edited_by_user": bool(a.edited_by_user),
                "instructions": a.instructions, "created_at": a.created_at, "run_id": str(a.run_id) if a.run_id else None,
            })
        out_versions.append({
            "id": str(v.id),
            "version_no": v.version_no,
            "is_current": v.id == project.current_version_id,
            "parent_version_id": str(v.parent_version_id) if v.parent_version_id else None,
            "idea_text": v.idea_text,
            "created_at": v.created_at,
            "understood": v.structured_idea is not None,
            "evaluations": [{"id": str(e.id), "overall_score": e.overall_score, "created_at": e.created_at,
                             "model_name": e.model_name} for e in evaluations],
            "artifacts": [
                {"artifact_type": t, "title": ARTIFACT_TITLES.get(t) or REPORT_TITLES.get(t, t), "versions": items}
                for t, items in grouped.items()
            ],
        })
    recent = db.scalars(
        select(AgentRun).where(AgentRun.project_id == project.id).where(AgentRun.parent_run_id.is_(None))
        .order_by(AgentRun.started_at.desc().nulls_first(), AgentRun.id).limit(runs)
    ).all()
    return {"project_id": str(project.id), "versions": out_versions, "runs": [run_dict(r) for r in recent]}


# ------------------------------------------------------------------ export

_MEDIA = {
    "pdf": "application/pdf",
    "md": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "zip": "application/zip",
}


@router.post("/export")
def export_project(
    format: ExportFormat = Query(default="pdf"),
    version: int | None = Query(default=None, ge=1),
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> Response:
    """Compile the project (idea, understanding, evaluation, reports, blueprint) as a download."""
    from app.services.export.bundle import collect, to_markdown
    from app.services.export.package import to_zip
    from app.services.export.pdf import to_pdf
    from app.services.export.word import to_docx

    target = _version_by_no(db, project, version) if version else _version_or_409(db, project)
    started = datetime.now(timezone.utc)
    bundle = collect(db, project, target)
    if format == "pdf":
        body = to_pdf(bundle)
    elif format == "docx":
        body = to_docx(bundle)
    elif format == "zip":
        body = to_zip(bundle)
    else:
        body = to_markdown(bundle).encode("utf-8")
    filename = f"{bundle.slug}.{format}"
    db.add(AgentRun(
        project_id=project.id, version_id=target.id, agent_name="export", status="succeeded",
        started_at=started, finished_at=datetime.now(timezone.utc), tokens_in=0, tokens_out=0,
        input_ref={"format": format, "version_no": target.version_no},
        output_ref={"filename": filename, "bytes": len(body), "sections": [s.key for s in bundle.sections],
                    "missing": bundle.missing},
    ))
    db.commit()
    return Response(
        content=body,
        media_type=_MEDIA[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "X-Export-Sections": ",".join(s.key for s in bundle.sections),
                 "Access-Control-Expose-Headers": "Content-Disposition, X-Export-Sections"},
    )
