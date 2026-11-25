"""Sliding-window rate limiter for the auth endpoints.

The window lives in process memory, which is enough for a single API process
(the lab set-up). With several API replicas each one keeps its own counts, so
move this to Redis before scaling out.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings


class SlidingWindowLimiter:
    def __init__(self, attempts: int, window_seconds: float) -> None:
        self.attempts = attempts
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, now: float | None = None) -> float | None:
        """Record one attempt. Return seconds to wait if over the limit, else None."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.attempts:
                return max(self.window - (now - hits[0]), 0.0)
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_settings = get_settings()
auth_limiter = SlidingWindowLimiter(
    _settings.auth_rate_limit_attempts, _settings.auth_rate_limit_window_seconds
)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def limit_auth(request: Request) -> None:
    """FastAPI dependency: cap login/register attempts per client IP and route."""
    key = f"{request.url.path}:{_client_ip(request)}"
    retry_after = auth_limiter.hit(key)
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many attempts. Please wait a minute and try again.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )
