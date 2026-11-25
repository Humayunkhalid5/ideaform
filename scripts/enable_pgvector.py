"""Switch ``embeddings.embedding`` from the REAL[] fallback to pgvector.

Migration 0001 creates ``embeddings.embedding`` as ``REAL[]`` when the server has
no pgvector build (stock Windows PostgreSQL). After installing pgvector
(``scripts/install_pgvector_windows.ps1``, or the ``pgvector/pgvector`` Docker
image), run this once. It is idempotent and safe to re-run.

    backend/.venv/Scripts/python scripts/enable_pgvector.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")


def main() -> None:
    from sqlalchemy import text

    from app.db.session import engine

    with engine.begin() as conn:
        available = conn.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        ).scalar()
        if not available:
            raise SystemExit(
                "pgvector is not installed on this PostgreSQL server. "
                "See scripts/install_pgvector_windows.ps1."
            )
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        column_type = conn.execute(
            text(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                "WHERE attrelid = 'embeddings'::regclass AND attname = 'embedding'"
            )
        ).scalar()
        if column_type and column_type.startswith("vector"):
            print(f"embeddings.embedding is already {column_type}")
        else:
            conn.execute(
                text(
                    "ALTER TABLE embeddings ALTER COLUMN embedding "
                    "TYPE vector(384) USING embedding::vector(384)"
                )
            )
            print(f"embeddings.embedding converted from {column_type} to vector(384)")
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw "
                "ON embeddings USING hnsw (embedding vector_cosine_ops)"
            )
        )
        print("HNSW index ready")


if __name__ == "__main__":
    main()
