"""HTTP fetcher: identifying User-Agent, size and type caps, 3 retries with backoff."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

RETRYABLE = {408, 425, 429, 500, 502, 503, 504}
TEXT_TYPES = ("text/html", "application/xhtml+xml", "text/plain", "text/markdown")
PDF_TYPE = "application/pdf"


@dataclass
class FetchResult:
    url: str
    final_url: str | None = None
    status: int | None = None
    content_type: str | None = None
    body: bytes = b""
    fetch_ms: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 300

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def fetch(url: str, *, client: httpx.Client | None = None, attempts: int = 3) -> FetchResult:
    settings = get_settings()
    own = client is None
    client = client or httpx.Client(
        timeout=settings.scraper_timeout_seconds,
        follow_redirects=True,
        headers={
            "User-Agent": settings.crawler_user_agent,
            "Accept": "text/html,application/xhtml+xml,text/plain,application/pdf;q=0.8",
            "Accept-Language": "en",
        },
    )
    result = FetchResult(url=url)
    started = time.perf_counter()
    try:
        for attempt in range(1, attempts + 1):
            try:
                with client.stream("GET", url) as resp:
                    result.status = resp.status_code
                    result.final_url = str(resp.url)
                    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
                    result.content_type = ctype or None
                    if resp.status_code in RETRYABLE and attempt < attempts:
                        result.error = f"HTTP {resp.status_code}"
                    elif resp.status_code >= 400:
                        result.error = f"HTTP {resp.status_code}"
                        break
                    elif ctype and not (ctype in TEXT_TYPES or ctype == PDF_TYPE):
                        result.error = f"unsupported content-type {ctype}"
                        break
                    else:
                        declared = int(resp.headers.get("content-length") or 0)
                        if declared > settings.scraper_max_bytes_per_page:
                            result.error = f"page larger than {settings.scraper_max_bytes_per_page} bytes"
                            break
                        chunks, size = [], 0
                        for part in resp.iter_bytes():
                            size += len(part)
                            if size > settings.scraper_max_bytes_per_page:
                                result.error = (
                                    f"page larger than {settings.scraper_max_bytes_per_page} bytes"
                                )
                                break
                            chunks.append(part)
                        result.body = b"".join(chunks)
                        if result.error is None:
                            break
                        break
            except httpx.HTTPError as exc:
                result.error = f"{type(exc).__name__}: {exc}"[:300]
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1) + random.random(), 8))
                result.error = None
    finally:
        if own:
            client.close()
        result.fetch_ms = int((time.perf_counter() - started) * 1000)
    if result.error is None and not result.ok:
        result.error = f"HTTP {result.status}"
    return result
