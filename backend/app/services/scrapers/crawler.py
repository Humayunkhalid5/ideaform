"""Crawl a list of URLs through guard -> fetch -> extract -> quality -> dedupe -> ingest.

Every URL gets a ``crawl_pages`` row (FR-RES-9) with the robots decision, HTTP
status, timing and content hash, whether or not it was stored.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.scrape import CrawlPage, ScrapeJob
from app.services.knowledge.ingest import DocumentIn, ingest_document
from app.services.knowledge.text import clean_text, content_hash, jaccard, shingles
from app.services.scrapers import adapters
from app.services.scrapers.fetcher import FetchResult, fetch
from app.services.scrapers.guard import DomainRateLimiter, RobotsCache, domain_of
from app.services.scrapers.quality import check_quality

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CrawlTarget:
    url: str
    discovery_source: str = "seed"  # tavily | seed | user | cache
    title_hint: str | None = None
    published_hint: str | None = None


@dataclass
class CrawlStats:
    requested: int = 0
    fetched: int = 0
    stored: int = 0
    skipped_robots: int = 0
    rejected: int = 0
    duplicates: int = 0
    source_ids: list[uuid.UUID] = field(default_factory=list)


def _maybe_render(url: str, result: FetchResult) -> FetchResult:
    """Re-fetch a JS-rendered page with Playwright when it is installed and enabled."""
    settings = get_settings()
    if not settings.scraper_playwright_enabled:
        return result
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return result
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=settings.crawler_user_agent)
            page.goto(url, timeout=settings.scraper_timeout_seconds * 1000)
            html = page.content()
            browser.close()
        result.body = html.encode("utf-8")
        result.content_type = "text/html"
        return result
    except Exception as exc:  # noqa: BLE001
        logger.info("playwright render failed for %s: %s", url, exc)
        return result


class Crawler:
    def __init__(
        self,
        db: Session,
        job: ScrapeJob,
        *,
        kb: str,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        category: str | None = None,
        topic_terms: list[str] | None = None,
        robots: RobotsCache | None = None,
        limiter: DomainRateLimiter | None = None,
        fetcher=fetch,
        deadline: float | None = None,
    ) -> None:
        settings = get_settings()
        self.db = db
        self.job = job
        self.kb = kb
        self.user_id = user_id
        self.project_id = project_id
        self.category = category
        self.topic_terms = topic_terms
        self.robots = robots or RobotsCache(settings.crawler_user_agent)
        self.limiter = limiter or DomainRateLimiter(settings.scraper_min_delay_seconds)
        self.fetch = fetcher
        self.deadline = deadline
        self.max_pages = settings.scraper_max_pages_per_run
        self.min_words = settings.scraper_min_words
        self.respect_robots = settings.scraper_respect_robots
        self._domain_sigs: dict[str, list[set[str]]] = {}

    def _log(self, target: CrawlTarget, **fields) -> CrawlPage:
        page = CrawlPage(
            job_id=self.job.id,
            url=target.url[:2000],
            domain=domain_of(target.url) or "unknown",
            discovery_source=target.discovery_source,
            **fields,
        )
        self.db.add(page)
        self.db.flush()
        return page

    def crawl(self, targets: list[CrawlTarget]) -> CrawlStats:
        stats = CrawlStats()
        seen: set[str] = set()
        self.job.status = "running"
        self.job.started_at = self.job.started_at or _utcnow()

        for target in targets:
            if target.url in seen:
                continue
            seen.add(target.url)
            if stats.fetched >= self.max_pages:
                break
            if self.deadline is not None and time.monotonic() > self.deadline:
                logger.info("crawl deadline reached; stopping with partial results")
                break
            stats.requested += 1
            self._crawl_one(target, stats)

        self.job.pages_requested = (self.job.pages_requested or 0) + stats.requested
        self.job.pages_fetched = (self.job.pages_fetched or 0) + stats.fetched
        self.job.pages_skipped_robots = (self.job.pages_skipped_robots or 0) + stats.skipped_robots
        self.job.pages_rejected = (self.job.pages_rejected or 0) + stats.rejected
        return stats

    def _crawl_one(self, target: CrawlTarget, stats: CrawlStats) -> None:
        adapter = adapters.select(target.url)
        fetch_url = adapter.fetch_url(target.url)
        domain = domain_of(fetch_url)

        decision = self.robots.check(fetch_url)
        if not decision.allowed and (self.respect_robots or decision.reason != "disallowed by robots.txt"):
            stats.skipped_robots += 1
            self._log(target, robots_allowed=False, skip_reason=decision.reason)
            return

        self.limiter.wait(domain, decision.crawl_delay)
        result = self.fetch(fetch_url)
        stats.fetched += 1
        if result.ok and result.content_type in (None, "text/html") and len(result.body) < 3_000:
            result = _maybe_render(fetch_url, result)

        common = dict(
            robots_allowed=True,
            final_url=result.final_url,
            http_status=result.status,
            content_type=result.content_type,
            fetch_ms=result.fetch_ms,
        )
        if not result.ok:
            stats.rejected += 1
            self._log(target, skip_reason="fetch failed", error_message=result.error, **common)
            return

        try:
            extracted = adapter.extract(target.url, result.body, result.content_type)
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the job
            extracted = None
            logger.info("extract failed for %s: %s", target.url, exc)
        if extracted is None:
            stats.rejected += 1
            self._log(target, skip_reason="no main text", **common)
            return

        text = clean_text(extracted.text)
        digest = content_hash(text)
        reason = check_quality(
            text, raw_size=len(result.body), min_words=self.min_words, topic_terms=self.topic_terms
        )
        if reason is None:
            sig = shingles(text[:20_000])
            seen_sigs = self._domain_sigs.setdefault(domain, [])
            if any(jaccard(sig, other) > 0.8 for other in seen_sigs):
                reason = "near-duplicate of another page on this domain"
            else:
                seen_sigs.append(sig)
        if reason:
            stats.rejected += 1
            self._log(target, skip_reason=reason, content_hash=digest, **common)
            return

        outcome = ingest_document(
            self.db,
            DocumentIn(
                title=extracted.title or target.title_hint or target.url,
                text=text,
                kb=self.kb,
                url=result.final_url or target.url,
                source_type=extracted.source_type,
                publisher=extracted.publisher,
                published_at=extracted.published_at,
                licence_note=extracted.licence_note,
                attribution=f"{extracted.publisher or domain}, retrieved {_utcnow():%Y-%m-%d}",
                category=self.category,
                adapter=adapter.name,
                user_id=self.user_id,
                project_id=self.project_id,
            ),
            min_words=self.min_words,
        )
        if outcome.status == "duplicate":
            stats.duplicates += 1
        if outcome.status == "rejected":
            stats.rejected += 1
            self._log(target, skip_reason=outcome.reason, content_hash=digest, **common)
            return
        if outcome.status == "created":
            stats.stored += 1
        if outcome.source_id and outcome.source_id not in stats.source_ids:
            stats.source_ids.append(outcome.source_id)
        self._log(
            target,
            content_hash=digest,
            source_id=outcome.source_id,
            skip_reason="duplicate content" if outcome.status == "duplicate" else None,
            **common,
        )
