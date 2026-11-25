"""Project CRUD, requirements editing and the extraction trigger."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.project import Project, ProjectRequirement, ProjectVersion
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectUpdate,
    RequirementOut,
    RequirementUpdateRequest,
    VersionOut,
)
from app.services.llm.base import LLMError
from app.services.quota import ensure_within_quota

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


def get_owned_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    return project


def current_version(db: Session, project: Project) -> ProjectVersion | None:
    if project.current_version_id is not None:
        version = db.get(ProjectVersion, project.current_version_id)
        if version is not None:
            return version
    return db.scalar(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project.id)
        .order_by(ProjectVersion.version_no.desc())
        .limit(1)
    )


def _requirements(db: Session, version: ProjectVersion | None) -> list[ProjectRequirement]:
    if version is None:
        return []
    return list(
        db.scalars(
            select(ProjectRequirement)
            .where(ProjectRequirement.version_id == version.id)
            # created_at ties when rows are inserted in one transaction
            .order_by(ProjectRequirement.created_at, ProjectRequirement.id)
        ).all()
    )


def _detail(db: Session, project: Project) -> ProjectDetail:
    version = current_version(db, project)
    detail = ProjectDetail.model_validate(project)
    detail.version = VersionOut.model_validate(version) if version else None
    detail.requirements = [RequirementOut.model_validate(r) for r in _requirements(db, version)]
    return detail


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(Project.user_id == current_user.id)
            .order_by(Project.updated_at.desc())
        ).all()
    )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetail:
    project = Project(
        user_id=current_user.id,
        title=payload.title,
        category=payload.category or "software",
        help_level=payload.help_level,
    )
    db.add(project)
    db.flush()

    version = ProjectVersion(project_id=project.id, version_no=1, idea_text=payload.idea_text)
    db.add(version)
    db.flush()
    project.current_version_id = version.id

    db.commit()
    db.refresh(project)
    return _detail(db, project)


@router.get("/{project_id}", response_model=ProjectDetail)
def read_project(
    project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
) -> ProjectDetail:
    return _detail(db, project)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> Project:
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete(
    "/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_project(
    project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
) -> None:
    db.delete(project)
    db.commit()


@router.get("/{project_id}/requirements", response_model=list[RequirementOut])
def list_requirements(
    project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
) -> list[ProjectRequirement]:
    return _requirements(db, current_version(db, project))


@router.patch("/{project_id}/requirements", response_model=list[RequirementOut])
def update_requirements(
    payload: RequirementUpdateRequest,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> list[ProjectRequirement]:
    version = _version_or_409(db, project)

    rows = {row.id: row for row in _requirements(db, version)}
    missing = [patch.id for patch in payload.requirements if patch.id not in rows]
    if missing:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Requirements not in this project: {', '.join(str(m) for m in missing)}",
        )

    for patch in payload.requirements:
        row = rows[patch.id]
        if patch.description is not None:
            row.description = patch.description
        if patch.priority is not None:
            row.priority = patch.priority
        if patch.confirmed is not None:
            row.confirmed = patch.confirmed
        row.source = "user"

    db.commit()
    return _requirements(db, version)


def _dispatch(
    db: Session,
    project: Project,
    version: ProjectVersion,
    agent_name: str,
    task_name: str,
    options: dict | None = None,
) -> dict[str, str]:
    """Create an ``agent_runs`` row and queue it on Celery, or run it inline."""
    options = options or {}
    run = AgentRun(
        project_id=project.id,
        version_id=version.id,
        agent_name=agent_name,
        status="queued",
        input_ref={"version_id": str(version.id), **options},
    )
    db.add(run)
    project.status = "analysing"
    db.commit()
    db.refresh(run)

    if not get_settings().jobs_inline:
        try:
            from app.worker import tasks

            getattr(tasks, task_name).delay(str(project.id), str(run.id), **options)
            return {"run_id": str(run.id), "status": "queued"}
        except Exception:  # broker unavailable: run here so the endpoint still works
            logger.warning("celery unavailable, running %s inline for %s", agent_name, project.id)

    from app.services.nlp import pipeline
    from app.services.research.agent import run_research

    runner = {
        "understand_idea": pipeline.run_understanding,
        "regenerate_requirements": pipeline.run_requirements,
        "research_project": run_research,
    }[task_name]
    try:
        runner(db, project.id, run.id, **options)
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Extraction failed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - run row already records the failure
        logger.exception("%s failed for %s", agent_name, project.id)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"{agent_name.capitalize()} failed: {exc}"
        ) from exc
    return {"run_id": str(run.id), "status": "succeeded"}


def _version_or_409(db: Session, project: Project) -> ProjectVersion:
    version = current_version(db, project)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Project has no idea version yet.")
    return version


@router.post("/{project_id}/understand", status_code=status.HTTP_202_ACCEPTED)
def understand_project(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Queue category classification + structured extraction for the current version."""
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    return _dispatch(db, project, version, "understanding", "understand_idea")


@router.post("/{project_id}/requirements/regenerate", status_code=status.HTTP_202_ACCEPTED)
def regenerate_requirements(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Re-extract requirements for the current version, keeping user-edited or confirmed rows."""
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    return _dispatch(db, project, version, "requirements", "regenerate_requirements")
