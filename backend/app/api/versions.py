"""Idea versions: list, create, read and restore (SRS: versioned ideas)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.projects import _detail, _requirements, current_version, get_owned_project
from app.db.session import get_db
from app.models.project import Project, ProjectRequirement, ProjectVersion
from app.schemas.project import (
    ProjectDetail,
    RequirementOut,
    VersionCreate,
    VersionDetail,
    VersionSummary,
)

router = APIRouter(prefix="/projects/{project_id}/versions", tags=["versions"])


def _get_version(db: Session, project: Project, version_no: int) -> ProjectVersion:
    version = db.scalar(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project.id)
        .where(ProjectVersion.version_no == version_no)
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found.")
    return version


def _current_id(db: Session, project: Project):
    current = current_version(db, project)
    return current.id if current else None


@router.get("", response_model=list[VersionSummary])
def list_versions(
    project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
) -> list[VersionSummary]:
    current_id = _current_id(db, project)
    versions = db.scalars(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project.id)
        .order_by(ProjectVersion.version_no.desc())
    ).all()
    return [
        VersionSummary(
            id=v.id,
            version_no=v.version_no,
            change_summary=v.change_summary,
            parent_version_id=v.parent_version_id,
            has_structure=v.structured_idea is not None,
            is_current=v.id == current_id,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_version(
    payload: VersionCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> ProjectDetail:
    """Add a new idea version on top of the current one and make it current.

    The new version starts without structure; call ``POST /projects/{id}/understand``
    to extract it.
    """
    parent = current_version(db, project)
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
        idea_text=payload.idea_text,
        change_summary=payload.change_summary,
        parent_version_id=parent.id if parent else None,
    )
    db.add(version)
    db.flush()

    if payload.copy_requirements and parent is not None:
        for row in _requirements(db, parent):
            db.add(
                ProjectRequirement(
                    version_id=version.id,
                    req_type=row.req_type,
                    description=row.description,
                    priority=row.priority,
                    source=row.source,
                    confirmed=False,
                )
            )

    project.current_version_id = version.id
    project.status = "draft"
    db.commit()
    db.refresh(project)
    return _detail(db, project)


@router.get("/{version_no}", response_model=VersionDetail)
def read_version(
    version_no: int,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> VersionDetail:
    version = _get_version(db, project, version_no)
    detail = VersionDetail.model_validate(version)
    detail.is_current = version.id == _current_id(db, project)
    detail.requirements = [RequirementOut.model_validate(r) for r in _requirements(db, version)]
    return detail


@router.post("/{version_no}/restore", response_model=ProjectDetail)
def restore_version(
    version_no: int,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
) -> ProjectDetail:
    """Make an earlier version current again. No data is copied or deleted."""
    version = _get_version(db, project, version_no)
    project.current_version_id = version.id
    project.status = "ready" if version.structured_idea is not None else "draft"
    db.commit()
    db.refresh(project)
    return _detail(db, project)
