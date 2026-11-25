"""Daily LLM token budget per user (SRS: DAILY_TOKEN_LIMIT_PER_USER)."""

from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.agent import AgentRun
from app.models.project import Project
from app.models.user import User


def _start_of_utc_day(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def tokens_used_today(db: Session, user_id) -> int:
    """Tokens (in + out) spent by the user's runs since 00:00 UTC."""
    total = db.scalar(
        select(
            func.coalesce(
                func.sum(
                    func.coalesce(AgentRun.tokens_in, 0) + func.coalesce(AgentRun.tokens_out, 0)
                ),
                0,
            )
        )
        .join(Project, Project.id == AgentRun.project_id)
        .where(Project.user_id == user_id)
        .where(func.coalesce(AgentRun.started_at, AgentRun.finished_at) >= _start_of_utc_day())
    )
    return int(total or 0)


def daily_limit(user: User) -> int:
    return user.daily_token_limit or get_settings().daily_token_limit_per_user


def ensure_within_quota(db: Session, user: User) -> None:
    """Raise 429 when the user has used up today's token budget."""
    limit = daily_limit(user)
    if limit <= 0:
        return
    used = tokens_used_today(db, user.id)
    if used >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily AI token limit reached ({used:,} of {limit:,}). It resets at 00:00 UTC.",
        )
