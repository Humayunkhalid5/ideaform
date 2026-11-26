"""Content-hash cache for model replies (Phase 5 cost control).

The key is a SHA-256 of everything that decides the answer: provider, model, the full
messages, the output schema, temperature, max tokens and reasoning effort. Only callers that
opt in (deterministic extraction on the fast tier) use it, so "regenerate" buttons still get
fresh output.

Backend: Redis when ``REDIS_URL`` answers a ping, otherwise the ``llm_cache`` table.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CachedReply:
    text: str
    model: str
    tokens_in: int
    tokens_out: int


def cache_key(**parts) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class DbCache:
    name = "postgres"

    def get(self, key: str) -> CachedReply | None:
        from app.db.session import SessionLocal
        from app.models.agent import LLMCache

        ttl = timedelta(hours=get_settings().llm_cache_ttl_hours)
        with SessionLocal() as db:
            row = db.get(LLMCache, key)
            if row is None:
                return None
            if row.created_at < datetime.now(timezone.utc) - ttl:
                db.delete(row)
                db.commit()
                return None
            row.hits = (row.hits or 0) + 1
            db.commit()
            return CachedReply(row.response, row.model or "", row.tokens_in, row.tokens_out)

    def set(self, key: str, reply: CachedReply) -> None:
        from app.db.session import SessionLocal
        from app.models.agent import LLMCache

        with SessionLocal() as db:
            row = db.get(LLMCache, key) or LLMCache(cache_key=key)
            row.model, row.response = reply.model, reply.text
            row.tokens_in, row.tokens_out = reply.tokens_in, reply.tokens_out
            row.created_at = datetime.now(timezone.utc)
            db.merge(row)
            db.commit()


class RedisCache:
    name = "redis"

    def __init__(self, client) -> None:
        self.client = client
        self.ttl = get_settings().llm_cache_ttl_hours * 3600

    def get(self, key: str) -> CachedReply | None:
        raw = self.client.get(f"llm:{key}")
        return CachedReply(**json.loads(raw)) if raw else None

    def set(self, key: str, reply: CachedReply) -> None:
        self.client.set(f"llm:{key}", json.dumps(reply.__dict__), ex=self.ttl)


@lru_cache
def get_cache() -> DbCache | RedisCache | None:
    settings = get_settings()
    if not settings.llm_cache_enabled:
        return None
    try:
        from redis import Redis

        client = Redis.from_url(settings.redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
        client.ping()
        return RedisCache(client)
    except Exception:  # noqa: BLE001 - no Redis locally is normal (JOBS_INLINE)
        return DbCache()


def lookup(key: str) -> CachedReply | None:
    cache = get_cache()
    if cache is None:
        return None
    try:
        return cache.get(key)
    except Exception as exc:  # noqa: BLE001 - a broken cache must never break a run
        logger.warning("llm cache read failed (%s)", exc)
        return None


def store(key: str, reply: CachedReply) -> None:
    cache = get_cache()
    if cache is None:
        return
    try:
        cache.set(key, reply)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm cache write failed (%s)", exc)
