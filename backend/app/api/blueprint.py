"""Blueprint (Phase 4): generate, list, regenerate one section, edit (architecture.md 8).

All endpoints are owner-only (others get 404), like the rest of ``/projects``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.evaluation import _version_by_no
from app.api.projects import _dispatch, _version_or_409, get_owned_project
from app.db.session import get_db
from app.models.agent import ProjectArtifact
from app.models.project import Project, ProjectVersion
from app.models.user import User
from app.schemas.blueprint import (
    BLUEPRINT_TYPES,
    ArtifactEdit,
    ArtifactOut,
    BlueprintOut,
    BlueprintType,
    RegenerateRequest,
)
from app.services.blueprint.agent import artifact_out, latest_artifacts, save_edit
from app.services.evaluation.agent import latest_evaluation
from app.services.quota import ensure_within_quota

router = APIRouter(prefix="/projects/{project_id}", tags=["blueprint"])
artifacts_router = APIRouter(prefix="/artifacts", tags=["blueprint"])


@router.post("/blueprint", status_code=status.HTTP_202_ACCEPTED)
def generate_blueprint(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Generate every blueprint section for the current version (understands it first if needed)."""
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    return _dispatch(db, project, version, "blueprint", "generate_blueprint", {"types": list(BLUEPRINT_TYPES)})


@router.get("/artifacts", response_model=BlueprintOut)
def list_artifacts(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    version: int | None = Query(default=None, ge=1, description="Version number; default current"),
) -> BlueprintOut:
    """The newest version of every blueprint section, plus which sections are missing."""
    target = _version_by_no(db, project, version) if version else _version_or_409(db, project)
    latest = latest_artifacts(db, target.id)
    return BlueprintOut(
        project_id=project.id,
        version_no=target.version_no,
        artifacts=[artifact_out(latest[t], latest) for t in BLUEPRINT_TYPES if t in latest],
        missing=[t for t in BLUEPRINT_TYPES if t not in latest],
        has_evaluation=latest_evaluation(db, target.id) is not None,
    )


@router.get("/artifacts/{artifact_type}/history", response_model=list[ArtifactOut])
def artifact_history(
    artifact_type: BlueprintType = Path(),
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    version: int | None = Query(default=None, ge=1),
) -> list[ArtifactOut]:
    """Every stored version of one section, newest first."""
    target = _version_by_no(db, project, version) if version else _version_or_409(db, project)
    rows = db.scalars(
        select(ProjectArtifact)
        .where(ProjectArtifact.version_id == target.id)
        .where(ProjectArtifact.artifact_type == artifact_type)
        .order_by(ProjectArtifact.artifact_version.desc())
    ).all()
    return [artifact_out(r) for r in rows]


@router.post("/artifacts/{artifact_type}/regenerate", status_code=status.HTTP_202_ACCEPTED)
def regenerate_artifact(
    payload: RegenerateRequest,
    artifact_type: BlueprintType = Path(),
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Regenerate one section alone, optionally following the user's instructions."""
    version = _version_or_409(db, project)
    ensure_within_quota(db, current_user)
    return _dispatch(
        db,
        project,
        version,
        "blueprint",
        "generate_blueprint",
        {"types": [artifact_type], "instructions": (payload.instructions or "").strip() or None},
    )


def _owned_artifact(db: Session, artifact_id: uuid.UUID, user: User) -> ProjectArtifact:
    row = db.get(ProjectArtifact, artifact_id)
    version = db.get(ProjectVersion, row.version_id) if row else None
    project = db.get(Project, version.project_id) if version else None
    if row is None or project is None or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found.")
    return row


@artifacts_router.get("/{artifact_id}", response_model=ArtifactOut)
def read_artifact(
    artifact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArtifactOut:
    row = _owned_artifact(db, artifact_id, current_user)
    return artifact_out(row, latest_artifacts(db, row.version_id))


@artifacts_router.patch("/{artifact_id}", response_model=ArtifactOut, status_code=status.HTTP_201_CREATED)
def edit_artifact(
    payload: ArtifactEdit,
    artifact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArtifactOut:
    """Save the user's edited Markdown as the next version of that section."""
    row = _owned_artifact(db, artifact_id, current_user)
    if payload.content.strip() == row.content.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Nothing changed.")
    edited = save_edit(db, row, payload.content)
    return artifact_out(edited, latest_artifacts(db, edited.version_id))
