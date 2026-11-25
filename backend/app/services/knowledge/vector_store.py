"""Embedding storage and cosine search.

Works with either column type migration 0001 may have created:

* ``VECTOR(384)`` (pgvector installed): search runs in SQL with ``<=>`` and HNSW.
* ``REAL[]`` (no pgvector): vectors are normalised, so cosine similarity is a dot
  product computed in Python over the *already scoped* candidate rows.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session


def _column_type(conn: Connection) -> str:
    return (
        conn.execute(
            text(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = 'embeddings'::regclass AND attname = 'embedding'"
            )
        ).scalar()
        or ""
    )


def uses_pgvector(db: Session) -> bool:
    """True when ``embeddings.embedding`` is a pgvector column (one catalog lookup)."""
    return _column_type(db.connection()).startswith("vector")


def _literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in vector) + "]"


def store_embeddings(
    db: Session, rows: list[tuple[uuid.UUID, list[float]]], model_name: str
) -> None:
    if not rows:
        return
    if uses_pgvector(db):
        stmt = text(
            "INSERT INTO embeddings (chunk_id, model_name, embedding) "
            "VALUES (:chunk_id, :model, CAST(:vec AS vector))"
        )
        params = [{"chunk_id": cid, "model": model_name, "vec": _literal(v)} for cid, v in rows]
    else:
        stmt = text(
            "INSERT INTO embeddings (chunk_id, model_name, embedding) "
            "VALUES (:chunk_id, :model, :vec)"
        )
        params = [{"chunk_id": cid, "model": model_name, "vec": v} for cid, v in rows]
    db.execute(stmt, params)


def semantic_search(
    db: Session,
    query_vector: list[float],
    where_sql: str,
    params: dict,
    k: int,
) -> list[tuple[uuid.UUID, float]]:
    """Top-``k`` chunk ids by cosine similarity among chunks matching ``where_sql``.

    ``where_sql`` is built by the retrieval layer from fixed fragments (never user
    text) and always contains the isolation rule; values travel in ``params``.
    """
    base = (
        "FROM research_chunks c JOIN research_sources s ON s.id = c.source_id "
        "JOIN embeddings e ON e.chunk_id = c.id "
        f"WHERE {where_sql}"
    )
    if uses_pgvector(db):
        rows = db.execute(
            text(
                f"SELECT c.id, 1 - (e.embedding <=> CAST(:qvec AS vector)) AS sim {base} "
                "ORDER BY e.embedding <=> CAST(:qvec AS vector) LIMIT :k"
            ),
            {**params, "qvec": _literal(query_vector), "k": k},
        ).all()
        return [(r[0], float(r[1])) for r in rows]

    rows = db.execute(text(f"SELECT c.id, e.embedding {base}"), params).all()
    if not rows:
        return []
    try:
        import numpy as np

        matrix = np.asarray([r[1] for r in rows], dtype="float32")
        sims = matrix @ np.asarray(query_vector, dtype="float32")
        order = np.argsort(-sims)[:k]
        return [(rows[i][0], float(sims[i])) for i in order]
    except ImportError:  # pragma: no cover - numpy ships with sentence-transformers
        scored = [(r[0], sum(a * b for a, b in zip(r[1], query_vector))) for r in rows]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
