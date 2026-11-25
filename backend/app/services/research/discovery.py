"""URL discovery behind a ``SearchProvider`` interface, implemented with Tavily.

* Tavily is used only to *discover* URLs; content is fetched by our scraper.
* Results are cached per (query, options) for ``TAVILY_CACHE_TTL_HOURS`` (7 days).
* A daily credit cap stops paid calls; on cap, quota or outage the client falls
  back to cached results (even expired), then to curated seed URLs (FR-RES-12).
* The API key is read from settings only and never logged or returned.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.search import SearchCache, SearchUsage

logger = logging.getLogger(__name__)

SEEDS_FILE = Path(__file__).resolve().parents[3] / "seed_urls.json"


@dataclass
class SearchHit:
    url: str
    title: str
    snippet: str = ""
    score: float = 0.0
    published_date: str | None = None
    origin: str = "tavily"  # tavily | cache | stale-cache | seed


class DiscoveryError(RuntimeError):
    pass


class SearchProvider(ABC):
    name: str

    @abstractmethod
    def search(self, db: Session, query: str, *, max_results: int, category: str | None = None) -> list[SearchHit]:
        """Return candidate URLs for ``query``. Never raises for quota/outage."""


def _cache_key(provider: str, query: str, depth: str, max_results: int) -> str:
    norm = " ".join(query.lower().split())
    return hashlib.sha256(f"{provider}|{depth}|{max_results}|{norm}".encode()).hexdigest()


def _today():
    return datetime.now(timezone.utc).date()


def credits_used_today(db: Session, provider: str = "tavily") -> int:
    row = db.get(SearchUsage, (_today(), provider))
    return row.credits if row else 0


def _record_usage(db: Session, provider: str, credits: int) -> None:
    row = db.get(SearchUsage, (_today(), provider))
    if row is None:
        row = SearchUsage(day=_today(), provider=provider, credits=0, requests=0)
        db.add(row)
    row.credits = (row.credits or 0) + credits
    row.requests = (row.requests or 0) + 1
    db.flush()


def seed_hits(category: str | None, limit: int) -> list[SearchHit]:
    """Curated fallback URLs per category (``backend/seed_urls.json``)."""
    try:
        seeds = json.loads(SEEDS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    urls = seeds.get(category or "", []) + seeds.get("general", [])
    return [SearchHit(url=u["url"], title=u.get("title", u["url"]), origin="seed") for u in urls[:limit]]


class TavilyProvider(SearchProvider):
    name = "tavily"

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = get_settings()
        self._transport = transport

    @property
    def credits_per_call(self) -> int:
        return 2 if self.settings.tavily_search_depth == "advanced" else 1

    def _call(self, query: str, max_results: int) -> list[SearchHit]:
        if not self.settings.tavily_api_key:
            raise DiscoveryError("TAVILY_API_KEY is not set")
        payload = {
            "query": query[:400],
            "search_depth": self.settings.tavily_search_depth,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,  # content comes from our own scraper
        }
        headers = {"Authorization": f"Bearer {self.settings.tavily_api_key}"}
        last = "unknown error"
        with httpx.Client(timeout=30, transport=self._transport) as client:
            for attempt in range(1, 4):
                try:
                    resp = client.post(f"{self.settings.tavily_base_url}/search", json=payload, headers=headers)
                except httpx.HTTPError as exc:
                    last = type(exc).__name__
                else:
                    if resp.status_code == 200:
                        data = resp.json()
                        return [
                            SearchHit(
                                url=r["url"],
                                title=r.get("title") or r["url"],
                                snippet=(r.get("content") or "")[:500],
                                score=float(r.get("score") or 0),
                                published_date=r.get("published_date"),
                            )
                            for r in data.get("results", [])
                            if r.get("url")
                        ]
                    last = f"HTTP {resp.status_code}"
                    if resp.status_code in (400, 401, 403, 432, 433):  # bad request, auth, quota
                        break
                if attempt < 3:
                    time.sleep(min(2 ** (attempt - 1) + random.random(), 8))
        raise DiscoveryError(f"Tavily search failed ({last})")

    def search(self, db: Session, query: str, *, max_results: int, category: str | None = None) -> list[SearchHit]:
        depth = self.settings.tavily_search_depth
        key = _cache_key(self.name, query, depth, max_results)
        cached = db.get(SearchCache, key)
        ttl = timedelta(hours=self.settings.tavily_cache_ttl_hours)
        if cached is not None and datetime.now(timezone.utc) - cached.created_at < ttl:
            return [SearchHit(**{**h, "origin": "cache"}) for h in cached.results]

        if credits_used_today(db, self.name) + self.credits_per_call > self.settings.tavily_daily_credit_cap:
            logger.warning("tavily daily credit cap reached; using fallbacks")
            return self._fallback(cached, category, max_results)

        try:
            hits = self._call(query, max_results)
        except DiscoveryError as exc:
            logger.warning("discovery failed for %r: %s; using fallbacks", query[:80], exc)
            return self._fallback(cached, category, max_results)

        _record_usage(db, self.name, self.credits_per_call)
        payload = [asdict(h) for h in hits]
        if cached is None:
            db.add(SearchCache(cache_key=key, provider=self.name, query=query, results=payload))
        else:
            cached.results = payload
            cached.created_at = datetime.now(timezone.utc)
        db.flush()
        return hits

    def _fallback(self, cached: SearchCache | None, category: str | None, limit: int) -> list[SearchHit]:
        if cached is not None:
            return [SearchHit(**{**h, "origin": "stale-cache"}) for h in cached.results]
        return seed_hits(category, limit)


def get_search_provider() -> SearchProvider:
    return TavilyProvider()


def cached_queries(db: Session, limit: int = 20) -> list[SearchCache]:
    return list(db.scalars(select(SearchCache).order_by(SearchCache.created_at.desc()).limit(limit)))
