"""Background run status."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.project import Project
from app.models.user import User

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}")
def read_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")

    project = db.get(Project, run.project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found.")

    return _run_dict(run)


def _run_dict(run: AgentRun) -> dict:
    return {
        "id": str(run.id),
        "project_id": str(run.project_id),
        "version_id": str(run.version_id) if run.version_id else None,
        "agent_name": run.agent_name,
        "status": run.status,
        "model_name": run.model_name,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "error_message": run.error_message,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "output": run.output_ref,
    }


@router.get("/project/{project_id}")
def list_project_runs(
    project_id: uuid.UUID,
    agent_name: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Recent runs of one project (newest first), optionally for one agent."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    stmt = select(AgentRun).where(AgentRun.project_id == project_id)
    if agent_name:
        stmt = stmt.where(AgentRun.agent_name == agent_name)
    stmt = stmt.order_by(AgentRun.started_at.desc().nulls_last(), AgentRun.id).limit(min(max(limit, 1), 50))
    return [_run_dict(r) for r in db.scalars(stmt)]
