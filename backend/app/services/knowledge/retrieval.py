"""Hybrid retrieval: semantic + keyword, reciprocal rank fusion, filters, rerank.

Isolation (FR-RES-7, AI_DESIGN 4.2 rule 1) is enforced here, in one place: every
query is limited to public KB-A/B plus KB-C rows of the *current* user and
project. Callers cannot turn it off; without a scope only KB-A/B is visible.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.knowledge.embeddings import embed_query
from app.services.knowledge.rerank import get_reranker
from app.services.knowledge.text import ENGLISH_STOPWORDS, jaccard, shingles, words
from app.services.knowledge.vector_store import semantic_search

MODES = ("hybrid", "vector", "keyword")
RRF_K = 60


@dataclass
class Scope:
    """Who is asking. KB-C is visible only for this exact user and project."""

    user_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


@dataclass
class Filters:
    kbs: list[str] | None = None  # subset of A, B, C
    categories: list[str] | None = None
    source_types: list[str] | None = None
    published_after: date | None = None
    include_restricted: bool = True


@dataclass
class Passage:
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    kb: str
    content: str
    title: str | None
    url: str | None
    publisher: str | None
    source_type: str | None
    published_at: date | None
    retrieved_at: datetime | None
    licence_note: str | None
    restricted: bool
    chunk_index: int
    score: float = 0.0
    ranks: dict = field(default_factory=dict)  # per-retriever rank, for explanations


def rrf(rank_lists: list[list], k: int = RRF_K) -> list:
    """Reciprocal rank fusion (AI_DESIGN 4.1)."""
    scores: dict = {}
    for ranks in rank_lists:
        for position, item in enumerate(ranks, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + position)
    return sorted(scores, key=lambda item: scores[item], reverse=True)


def build_where(scope: Scope, filters: Filters) -> tuple[str, dict]:
    """SQL predicate over ``c`` (research_chunks) and ``s`` (research_sources)."""
    clauses: list[str] = []
    params: dict = {}

    if scope.user_id is not None and scope.project_id is not None:
        clauses.append(
            "(c.kb IN ('A','B') OR (c.kb = 'C' AND c.user_id = :scope_user "
            "AND c.project_id = :scope_project))"
        )
        params["scope_user"] = scope.user_id
        params["scope_project"] = scope.project_id
    else:
        clauses.append("c.kb IN ('A','B')")

    if filters.kbs:
        clauses.append("c.kb = ANY(:kbs)")
        params["kbs"] = [k for k in filters.kbs if k in ("A", "B", "C")] or ["-"]
    if filters.categories:
        clauses.append("(s.category = ANY(:categories) OR s.category IS NULL OR c.kb = 'C')")
        params["categories"] = filters.categories
    if filters.source_types:
        clauses.append("s.source_type = ANY(:source_types)")
        params["source_types"] = filters.source_types
    if filters.published_after:
        clauses.append("(s.published_at IS NULL OR s.published_at >= :published_after)")
        params["published_after"] = filters.published_after
    if not filters.include_restricted:
        clauses.append("s.restricted IS NOT TRUE")
    return " AND ".join(clauses), params


_TERM = re.compile(r"^[a-z][a-z0-9\-']{1,40}$")


def keyword_terms(query: str, limit: int = 12) -> list[str]:
    seen: list[str] = []
    for token in words(query):
        token = token.strip("'-")
        if token in ENGLISH_STOPWORDS or len(token) < 3 or not _TERM.match(token):
            continue
        if token not in seen:
            seen.append(token)
    return seen[:limit]


def keyword_search(
    db: Session, query: str, where_sql: str, params: dict, k: int
) -> list[tuple[uuid.UUID, float]]:
    """PostgreSQL full-text search, OR of the query's content words, ranked by ts_rank_cd."""
    terms = keyword_terms(query)
    if not terms:
        return []
    # terms are [a-z0-9-] only, so they are safe inside to_tsquery. Any-term matches
    # are recalled; passages containing every term, and more distinct terms, rank
    # first; normalisation 1|32 damps the bias towards long passages.
    any_terms = " | ".join(t.replace("'", "") for t in terms)
    all_terms = " & ".join(t.replace("'", "") for t in terms)
    rows = db.execute(
        text(
            "SELECT c.id, ts_rank_cd(c.tsv, q, 1|32) "
            "+ CASE WHEN c.tsv @@ qa THEN 1.0 ELSE 0 END "
            "+ ts_rank(c.tsv, q, 0) AS rank "
            "FROM research_chunks c JOIN research_sources s ON s.id = c.source_id, "
            "to_tsquery('english', :tsq) q, to_tsquery('english', :tsq_all) qa "
            f"WHERE c.tsv @@ q AND {where_sql} "
            "ORDER BY rank DESC LIMIT :k"
        ),
        {**params, "tsq": any_terms, "tsq_all": all_terms, "k": k},
    ).all()
    return [(r[0], float(r[1])) for r in rows]


def _load_passages(db: Session, chunk_ids: list[uuid.UUID]) -> dict[uuid.UUID, Passage]:
    if not chunk_ids:
        return {}
    rows = db.execute(
        text(
            "SELECT c.id, c.source_id, c.kb, c.content, c.chunk_index, s.title, s.url, "
            "s.publisher, s.source_type, s.published_at, s.retrieved_at, s.licence_note, "
            "s.restricted FROM research_chunks c JOIN research_sources s ON s.id = c.source_id "
            "WHERE c.id = ANY(:ids)"
        ),
        {"ids": chunk_ids},
    ).all()
    return {
        r.id: Passage(
            chunk_id=r.id,
            source_id=r.source_id,
            kb=r.kb,
            content=r.content,
            chunk_index=r.chunk_index,
            title=r.title,
            url=r.url,
            publisher=r.publisher,
            source_type=r.source_type,
            published_at=r.published_at,
            retrieved_at=r.retrieved_at,
            licence_note=r.licence_note,
            restricted=bool(r.restricted),
        )
        for r in rows
    }


def _diversify(passages: list[Passage], max_per_source: int, limit: int) -> list[Passage]:
    """Drop near-duplicates from the same source and cap passages per source (rule 4)."""
    kept: list[Passage] = []
    per_source: dict[uuid.UUID, list[set[str]]] = {}
    for p in passages:
        sigs = per_source.setdefault(p.source_id, [])
        if len(sigs) >= max_per_source:
            continue
        sig = shingles(p.content)
        if any(jaccard(sig, other) > 0.6 for other in sigs):
            continue
        sigs.append(sig)
        kept.append(p)
        if len(kept) >= limit:
            break
    return kept


def search(
    db: Session,
    query: str,
    *,
    scope: Scope | None = None,
    filters: Filters | None = None,
    mode: str = "hybrid",
    rerank: bool = True,
    k: int | None = None,
) -> list[Passage]:
    """Return the top passages for ``query`` with source metadata for citations."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    settings = get_settings()
    scope = scope or Scope()
    filters = filters or Filters()
    k = k or settings.retrieval_final_k
    query = (query or "").strip()
    if not query:
        return []

    where_sql, params = build_where(scope, filters)
    lists: list[list[uuid.UUID]] = []
    ranks: dict[uuid.UUID, dict] = {}

    if mode in ("hybrid", "vector"):
        semantic = semantic_search(
            db, embed_query(query), where_sql, params, settings.retrieval_semantic_k
        )
        lists.append([cid for cid, _ in semantic])
        for pos, (cid, sim) in enumerate(semantic, start=1):
            ranks.setdefault(cid, {})["vector"] = pos
    if mode in ("hybrid", "keyword"):
        keyword = keyword_search(db, query, where_sql, params, settings.retrieval_keyword_k)
        lists.append([cid for cid, _ in keyword])
        for pos, (cid, _) in enumerate(keyword, start=1):
            ranks.setdefault(cid, {})["keyword"] = pos

    fused = rrf(lists) if len(lists) > 1 else (lists[0] if lists else [])
    candidates = fused[: max(settings.retrieval_rerank_k, k)]
    by_id = _load_passages(db, candidates)
    ordered = [by_id[c] for c in candidates if c in by_id]
    for position, passage in enumerate(ordered, start=1):
        passage.ranks = ranks.get(passage.chunk_id, {})
        passage.score = 1.0 / (RRF_K + position)

    reranker = get_reranker() if (rerank and mode == "hybrid") else None
    if reranker is not None and ordered:
        scores = reranker.score(query, [p.content for p in ordered])
        for passage, s in zip(ordered, scores):
            passage.score = s
            passage.ranks["rerank"] = True
        ordered.sort(key=lambda p: p.score, reverse=True)

    return _diversify(ordered, settings.retrieval_max_per_source, k)


def format_evidence(passages: list[Passage], max_chars: int = 900) -> str:
    """Numbered evidence block for grounded generation (AI_DESIGN 4.3)."""
    lines = []
    for i, p in enumerate(passages, start=1):
        when = p.published_at.isoformat() if p.published_at else (
            p.retrieved_at.date().isoformat() if p.retrieved_at else "n.d."
        )
        body = p.content if len(p.content) <= max_chars else p.content[:max_chars] + "…"
        lines.append(f"[E{i}] (source: {p.title or 'untitled'}, {when}, {p.url or 'no url'}) {body}")
    return "\n".join(lines)
