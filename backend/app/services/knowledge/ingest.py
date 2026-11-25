"""Ingestion pipeline: clean -> hash/dedupe -> chunk -> tag -> embed -> store.

Every knowledge base goes through ``ingest_document``: the seed scripts (KB-A/B),
the Research Agent's scraped pages and user uploads (KB-C).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.research import ResearchChunk, ResearchSource
from app.services.knowledge.embeddings import get_embedder
from app.services.knowledge.text import chunk_text, clean_text, content_hash, word_count
from app.services.knowledge.vector_store import store_embeddings

logger = logging.getLogger(__name__)

KBS = ("A", "B", "C")
NIL_UUID = uuid.UUID(int=0)


@dataclass
class DocumentIn:
    """One document in the normalised shape every adapter produces."""

    title: str
    text: str
    kb: str
    url: str | None = None
    source_type: str | None = None  # wikipedia, worldbank, arxiv, hackernews, github, docs, web, upload, note, dataset
    publisher: str | None = None
    published_at: date | None = None
    licence_note: str | None = None
    attribution: str | None = None
    category: str | None = None  # business | software | technology | general
    adapter: str | None = None
    restricted: bool = False
    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class IngestResult:
    status: str  # created | duplicate | rejected
    source_id: uuid.UUID | None = None
    chunks: int = 0
    reason: str | None = None


def _validate(doc: DocumentIn) -> str | None:
    if doc.kb not in KBS:
        return f"unknown kb {doc.kb!r}"
    if doc.kb == "C" and (doc.user_id is None or doc.project_id is None):
        return "KB-C documents need a user and a project"
    if doc.kb in ("A", "B"):
        if doc.user_id is not None or doc.project_id is not None:
            return "public KB-A/B documents must not carry a user or project"
        # AI_DESIGN 3.7 rule 3: licence and attribution are mandatory for shared KBs
        if not (doc.licence_note and doc.attribution):
            return "licence and attribution are required for KB-A/B"
    return None


def find_duplicate(db: Session, digest: str, project_id: uuid.UUID | None) -> uuid.UUID | None:
    return db.scalar(
        select(ResearchSource.id)
        .where(ResearchSource.content_hash == digest)
        .where(func.coalesce(ResearchSource.project_id, NIL_UUID) == (project_id or NIL_UUID))
    )


def ingest_document(db: Session, doc: DocumentIn, *, min_words: int = 20) -> IngestResult:
    """Store one document with its chunks and embeddings. The caller commits."""
    problem = _validate(doc)
    if problem:
        return IngestResult("rejected", reason=problem)

    text = clean_text(doc.text)
    if word_count(text) < min_words:
        return IngestResult("rejected", reason=f"too short ({word_count(text)} words)")

    digest = content_hash(text)
    existing = find_duplicate(db, digest, doc.project_id)
    if existing is not None:
        return IngestResult("duplicate", source_id=existing, reason="same content_hash in scope")

    settings = get_settings()
    pieces = chunk_text(text, settings.chunk_words, settings.chunk_overlap_words)
    if not pieces:
        return IngestResult("rejected", reason="no chunks")

    source = ResearchSource(
        kb=doc.kb,
        user_id=doc.user_id,
        project_id=doc.project_id,
        url=doc.url,
        title=(doc.title or "Untitled")[:500],
        publisher=doc.publisher,
        source_type=doc.source_type,
        published_at=doc.published_at,
        licence_note=doc.licence_note,
        attribution=doc.attribution,
        restricted=doc.restricted,
        adapter=doc.adapter,
        content_hash=digest,
        category=doc.category,
    )
    db.add(source)
    db.flush()

    chunk_rows = []
    for piece in pieces:
        # the heading path travels with the passage so citations keep their context
        body = f"{piece.heading}: {piece.text}" if piece.heading else piece.text
        row = ResearchChunk(
            source_id=source.id,
            kb=doc.kb,
            user_id=doc.user_id,
            project_id=doc.project_id,
            chunk_index=piece.index,
            content=body,
            token_count=piece.word_count,
        )
        db.add(row)
        chunk_rows.append(row)
    db.flush()

    embedder = get_embedder()
    # title is prepended for the vector only, which helps short passages match
    vectors = embedder.embed([f"{source.title}. {row.content}" for row in chunk_rows])
    store_embeddings(db, [(row.id, vec) for row, vec in zip(chunk_rows, vectors)], embedder.model_name)
    return IngestResult("created", source_id=source.id, chunks=len(chunk_rows))
