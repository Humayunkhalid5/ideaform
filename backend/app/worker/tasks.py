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


@celery_app.task(name="ideaform.evaluate_project", bind=True, max_retries=1)
def evaluate_project(self, project_id: str, run_id: str | None = None) -> dict:
    """Evaluation Agent: six dimensions, critique, competitors, business model."""
    from app.services.evaluation.agent import run_evaluation

    db = SessionLocal()
    try:
        return run_evaluation(db, uuid.UUID(project_id), uuid.UUID(run_id) if run_id else None)
    except Exception as exc:
        logger.exception("evaluate_project failed for %s", project_id)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        raise
    finally:
        db.close()


@celery_app.task(name="ideaform.improve_project", bind=True, max_retries=0)
def improve_project(
    self,
    project_id: str,
    run_id: str | None = None,
    evaluation_id: str | None = None,
    changes: list[dict] | None = None,
    note: str | None = None,
) -> dict:
    """Improvement loop: rewrite the idea, create the next version, re-evaluate it.

    Not retried: a retry would create a second version.
    """
    from app.services.evaluation.improve import run_improvement

    db = SessionLocal()
    try:
        return run_improvement(
            db,
            uuid.UUID(project_id),
            uuid.UUID(run_id) if run_id else None,
            evaluation_id=evaluation_id,
            changes=changes or [],
            note=note,
        )
    finally:
        db.close()


@celery_app.task(name="ideaform.generate_blueprint", bind=True, max_retries=0)
def generate_blueprint(
    self,
    project_id: str,
    run_id: str | None = None,
    types: list[str] | None = None,
    instructions: str | None = None,
) -> dict:
    """Blueprint: generate all sections, or regenerate one with optional instructions.

    Not retried: finished sections are already stored, and a retry would add versions.
    """
    from app.services.blueprint.agent import run_blueprint

    db = SessionLocal()
    try:
        return run_blueprint(
            db,
            uuid.UUID(project_id),
            uuid.UUID(run_id) if run_id else None,
            types=types,
            instructions=instructions,
        )
    finally:
        db.close()
