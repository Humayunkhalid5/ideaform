"""Discovery (Tavily) result cache and daily credit usage."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SearchCache(Base):
    """One cached discovery response, keyed by provider + normalised query + options."""

    __tablename__ = "search_cache"

    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    results: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SearchUsage(Base):
    """Credits spent per provider per UTC day (the spend cap reads this)."""

    __tablename__ = "search_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, primary_key=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
