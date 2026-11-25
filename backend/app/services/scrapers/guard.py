"""Permission guard: robots.txt (cached per domain), Crawl-delay, per-domain rate limit.

FR-RES-8: robots.txt, terms and per-domain rate limits are checked before every
fetch and the decision is recorded. A URL is never fetched when robots.txt
disallows it for our User-Agent (AI_DESIGN 10.2: zero violations).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.config import get_settings

# Hosts we never fetch: search-engine result pages (against their terms) and
# auth-walled social networks.
BLOCKED_HOSTS = (
    "google.", "bing.com", "duckduckgo.com", "search.yahoo.", "yandex.",
    "facebook.com", "instagram.com", "linkedin.com", "x.com", "twitter.com",
    "tiktok.com",
)
ROBOTS_TTL_SECONDS = 24 * 3600


@dataclass
class Decision:
    allowed: bool
    reason: str | None = None  # why it was blocked, for crawl_pages.skip_reason
    crawl_delay: float | None = None


def domain_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def host_blocked(host: str) -> bool:
    return any(host == b.rstrip(".") or host.startswith(b) or f".{b}" in f".{host}"
               for b in BLOCKED_HOSTS)


class RobotsCache:
    def __init__(self, user_agent: str, fetch=None, ttl: float = ROBOTS_TTL_SECONDS) -> None:
        self.user_agent = user_agent
        self.ttl = ttl
        self._fetch = fetch or self._http_fetch
        self._cache: dict[str, tuple[float, RobotFileParser | None, str | None]] = {}
        self._lock = threading.Lock()

    def _http_fetch(self, robots_url: str) -> tuple[int, str]:
        settings = get_settings()
        with httpx.Client(
            timeout=settings.scraper_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            resp = client.get(robots_url)
            return resp.status_code, resp.text

    def _load(self, scheme: str, host: str) -> tuple[RobotFileParser | None, str | None]:
        """Parser, or None meaning "everything allowed"; second item is a block reason."""
        robots_url = f"{scheme}://{host}/robots.txt"
        try:
            status, body = self._fetch(robots_url)
        except Exception:  # noqa: BLE001 - unreachable robots: be conservative
            return None, "robots.txt unreachable"
        if status in (401, 403):
            return None, f"robots.txt returned {status}"
        if status >= 500:
            return None, f"robots.txt returned {status}"
        if status >= 400:  # 404 etc.: no robots file, crawling allowed
            return None, None
        parser = RobotFileParser()
        parser.parse(body.splitlines())
        return parser, None

    def check(self, url: str) -> Decision:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return Decision(False, "not an http(s) URL")
        host = parts.hostname.lower()
        if host_blocked(host):
            return Decision(False, "host excluded by terms policy")

        key = f"{parts.scheme}://{host}"
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
        if cached is None or now - cached[0] > self.ttl:
            parser, reason = self._load(parts.scheme, host)
            cached = (now, parser, reason)
            with self._lock:
                self._cache[key] = cached
        _, parser, reason = cached

        if reason:
            return Decision(False, reason)
        if parser is None:
            return Decision(True)
        if not parser.can_fetch(self.user_agent, url):
            return Decision(False, "disallowed by robots.txt")
        delay = parser.crawl_delay(self.user_agent)
        return Decision(True, crawl_delay=float(delay) if delay else None)


class DomainRateLimiter:
    """At most one request per ``delay`` seconds per domain (token bucket of size 1)."""

    def __init__(self, min_delay: float, clock=time.monotonic, sleep=time.sleep) -> None:
        self.min_delay = min_delay
        self._clock = clock
        self._sleep = sleep
        self._next_ok: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, domain: str, crawl_delay: float | None = None) -> float:
        """Block until ``domain`` may be hit again; return the seconds waited."""
        delay = max(self.min_delay, crawl_delay or 0.0)
        with self._lock:
            now = self._clock()
            ready_at = self._next_ok.get(domain, now)
            wait = max(0.0, ready_at - now)
            self._next_ok[domain] = max(now, ready_at) + delay
        if wait:
            self._sleep(wait)
        return wait
