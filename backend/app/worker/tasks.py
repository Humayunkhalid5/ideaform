"""Celery tasks."""

from __future__ import annotations

import logging
import uuid

from app.db.session import SessionLocal
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ideaform.understand_idea", bind=True, max_retries=2)
def understand_idea(self, project_id: str, run_id: str | None = None) -> dict:
    """Classify and extract one project's current idea version."""
    from app.services.nlp.pipeline import run_understanding

    db = SessionLocal()
    try:
        return run_understanding(
            db,
            uuid.UUID(project_id),
            uuid.UUID(run_id) if run_id else None,
        )
    except Exception as exc:
        logger.exception("understand_idea failed for %s", project_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        raise
    finally:
        db.close()


@celery_app.task(name="ideaform.regenerate_requirements", bind=True, max_retries=2)
def regenerate_requirements(self, project_id: str, run_id: str | None = None) -> dict:
    """Re-extract requirements for one project's current idea version."""
    from app.services.nlp.pipeline import run_requirements

    db = SessionLocal()
    try:
        return run_requirements(
            db,
            uuid.UUID(project_id),
            uuid.UUID(run_id) if run_id else None,
        )
    except Exception as exc:
        logger.exception("regenerate_requirements failed for %s", project_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        raise
    finally:
        db.close()
