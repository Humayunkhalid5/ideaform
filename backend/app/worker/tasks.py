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


@celery_app.task(name="ideaform.research_project", bind=True, max_retries=1)
def research_project(
    self,
    project_id: str,
    run_id: str | None = None,
    extra_queries: list[str] | None = None,
    extra_urls: list[str] | None = None,
) -> dict:
    """Research Agent v1: plan, discover, crawl into KB-C, retrieve evidence."""
    from app.services.research.agent import run_research

    db = SessionLocal()
    try:
        return run_research(
            db,
            uuid.UUID(project_id),
            uuid.UUID(run_id) if run_id else None,
            extra_queries=extra_queries,
            extra_urls=extra_urls,
        )
    except Exception as exc:
        logger.exception("research_project failed for %s", project_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        raise
    finally:
        db.close()
