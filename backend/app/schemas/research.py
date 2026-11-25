"""Research, sources, documents and retrieval schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

KB = Literal["A", "B", "C"]
Mode = Literal["hybrid", "vector", "keyword"]


class ResearchRequest(BaseModel):
    # extra queries and URLs the user wants included (optional)
    queries: list[str] = Field(default_factory=list, max_length=4)
    urls: list[HttpUrl] = Field(default_factory=list, max_length=10)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kb: KB
    title: str | None = None
    url: str | None = None
    publisher: str | None = None
    source_type: str | None = None
    published_at: date | None = None
    retrieved_at: datetime
    licence_note: str | None = None
    attribution: str | None = None
    restricted: bool = False
    adapter: str | None = None
    category: str | None = None
    chunk_count: int = 0
    preview: str | None = None


class PassageOut(BaseModel):
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    kb: KB
    chunk_index: int
    content: str
    title: str | None = None
    url: str | None = None
    publisher: str | None = None
    source_type: str | None = None
    published_at: date | None = None
    retrieved_at: datetime | None = None
    licence_note: str | None = None
    score: float = 0.0
    ranks: dict = Field(default_factory=dict)


class SourceDetail(SourceOut):
    passages: list[PassageOut] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    kbs: list[KB] | None = None
    categories: list[str] | None = None
    source_types: list[str] | None = None
    published_after: date | None = None
    mode: Mode = "hybrid"
    rerank: bool = True
    k: int = Field(default=8, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    mode: Mode
    passages: list[PassageOut]
    evidence_block: str


class CrawlPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    final_url: str | None = None
    domain: str
    http_status: int | None = None
    robots_allowed: bool
    skip_reason: str | None = None
    content_type: str | None = None
    fetch_ms: int | None = None
    discovery_source: str | None = None
    content_hash: str | None = None
    source_id: uuid.UUID | None = None
    error_message: str | None = None
    fetched_at: datetime


class ScrapeJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID | None = None
    adapter: str
    status: str
    pages_requested: int | None = None
    pages_fetched: int | None = None
    pages_skipped_robots: int | None = None
    pages_rejected: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pages: list[CrawlPageOut] = Field(default_factory=list)


class DocumentUploadOut(BaseModel):
    status: Literal["created", "duplicate"]
    source: SourceOut


class KnowledgeStats(BaseModel):
    kb: dict[str, int]
    chunks: dict[str, int]
    embedding_column: str
    tavily_credits_today: int
    tavily_daily_cap: int
