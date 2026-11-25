"""Research Agent v1 (AI_DESIGN 6.3).

1. Plan 4-8 queries from the structured idea (fast tier; template fallback).
2. Discover candidate URLs with Tavily (cached, capped; stale cache and seeds as fallback).
3. Crawl permitted pages through the robots/rate-limit guard and store them as
   private project knowledge (KB-C) with provenance in ``scrape_jobs``/``crawl_pages``.
4. Retrieve evidence per query with hybrid search across KB-A/B/C.
5. List questions the evidence does not answer.

Competitor extraction (step 4 of the design) belongs to Phase 3 task 3.4.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.scrape import ScrapeJob
from app.services.knowledge.retrieval import Scope, keyword_terms, search
from app.services.nlp.pipeline import _fail_run, _load, _start_run
from app.services.research.discovery import SearchHit, get_search_provider
from app.services.research.planner import ResearchQuery, plan_queries
from app.services.scrapers.crawler import CrawlTarget, Crawler

logger = logging.getLogger(__name__)

MIN_EVIDENCE = 2


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _interleave(per_query: list[list[SearchHit]], limit: int) -> list[SearchHit]:
    """Round-robin across queries so one query cannot use the whole page budget."""
    out, seen = [], set()
    depth = max((len(h) for h in per_query), default=0)
    for i in range(depth):
        for hits in per_query:
            if i < len(hits) and hits[i].url not in seen:
                seen.add(hits[i].url)
                out.append(hits[i])
                if len(out) >= limit:
                    return out
    return out


def run_research(
    db: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    *,
    extra_queries: list[str] | None = None,
    extra_urls: list[str] | None = None,
    crawler_factory=None,
    provider=None,
) -> dict:
    settings = get_settings()
    project, version = _load(db, project_id)
    status_on_failure = project.status if project.status in ("ready", "draft") else "ready"
    run = _start_run(db, run_id)
    started = time.monotonic()

    try:
        structured = version.structured_idea or {}
        planned, plan_result = plan_queries(structured, version.idea_text, project.title)
        queries: list[ResearchQuery] = list(planned)
        for q in extra_queries or []:
            if q.strip():
                queries.insert(0, ResearchQuery(query=q.strip()[:300], intent="competitors"))
        queries = queries[: settings.research_max_queries + len(extra_queries or [])]

        provider = provider or get_search_provider()
        per_query: list[list[SearchHit]] = []
        query_log = []
        for q in queries:
            hits = provider.search(
                db, q.query, max_results=settings.tavily_max_results, category=project.category
            )
            per_query.append(hits)
            query_log.append(
                {
                    "query": q.query,
                    "intent": q.intent,
                    "hits": len(hits),
                    "origin": hits[0].origin if hits else "none",
                }
            )
        db.commit()  # keep cache/usage rows even if crawling fails later

        hits = _interleave(per_query, settings.tavily_results_per_run)
        targets = [CrawlTarget(url=u.strip(), discovery_source="user") for u in (extra_urls or []) if u.strip()]
        targets += [
            CrawlTarget(url=h.url, discovery_source=h.origin, title_hint=h.title) for h in hits
        ]

        job = ScrapeJob(
            project_id=project.id,
            run_id=run.id if run else None,
            adapter="research_agent",
            seed_urls=[t.url for t in targets],
            status="running",
            started_at=_utcnow(),
        )
        db.add(job)
        db.flush()

        topic = " ".join(
            [project.title, structured.get("problem", "")]
            + list(structured.get("key_features") or [])
            + list(structured.get("target_users") or [])
        ) or version.idea_text
        crawler = (crawler_factory or Crawler)(
            db,
            job,
            kb="C",
            user_id=project.user_id,
            project_id=project.id,
            category=project.category,
            topic_terms=keyword_terms(topic, limit=25),
            deadline=started + settings.research_max_seconds,
        )
        stats = crawler.crawl(targets)
        job.status = "succeeded"
        job.finished_at = _utcnow()
        db.commit()

        scope = Scope(user_id=project.user_id, project_id=project.id)
        evidence = []
        unanswered = []
        for q in queries:
            passages = search(db, q.query, scope=scope, k=5)
            evidence.append(
                {
                    "query": q.query,
                    "passages": [
                        {"chunk_id": str(p.chunk_id), "source_id": str(p.source_id), "kb": p.kb,
                         "title": p.title, "url": p.url}
                        for p in passages
                    ],
                }
            )
            if len(passages) < MIN_EVIDENCE:
                unanswered.append(q.query)

        summary = {
            "queries": query_log,
            "pages_requested": stats.requested,
            "pages_fetched": stats.fetched,
            "pages_stored": stats.stored,
            "pages_skipped_robots": stats.skipped_robots,
            "pages_rejected": stats.rejected,
            "duplicates": stats.duplicates,
            "sources": len(stats.source_ids),
            "scrape_job_id": str(job.id),
            "unanswered_questions": unanswered,
            "evidence": evidence,
            "seconds": round(time.monotonic() - started, 1),
        }
        project.status = "ready"
        if run is not None:
            run.status = "succeeded"
            run.finished_at = _utcnow()
            run.model_name = plan_result.model if plan_result else None
            run.tokens_in = plan_result.tokens_in if plan_result else 0
            run.tokens_out = plan_result.tokens_out if plan_result else 0
            run.output_ref = summary
        db.commit()
        return summary

    except Exception as exc:
        logger.exception("research failed for %s", project_id)
        _fail_run(db, project, run_id, exc, status_on_failure)
        raise
