"""Load the collected seed corpus into KB-A/KB-B: clean, dedupe, chunk, embed, store.

Idempotent: documents already stored (same content hash) are reported as
duplicates, so re-running after a new ``collect.py`` only adds what is new.
Writes a summary to ``data/knowledge_seed/kb_manifest.json``.

    backend/.venv/Scripts/python scripts/seed_kb/ingest.py              # every *.jsonl
    backend/.venv/Scripts/python scripts/seed_kb/ingest.py --only arxiv notes
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import COLLECTED, MANIFEST, read_jsonl, use_backend  # noqa: E402

use_backend()

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.research import ResearchChunk, ResearchSource  # noqa: E402
from app.services.knowledge.embeddings import get_embedder  # noqa: E402
from app.services.knowledge.ingest import DocumentIn, ingest_document  # noqa: E402


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the KB seed corpus.")
    parser.add_argument("--only", nargs="*", help="jsonl names without extension")
    args = parser.parse_args()

    files = sorted(COLLECTED.glob("*.jsonl"))
    if args.only:
        files = [f for f in files if f.stem in args.only]
    if not files:
        raise SystemExit(f"Nothing to ingest in {COLLECTED}. Run collect.py / add_documents.py first.")

    print(f"embedding model: {get_embedder().model_name}")
    db = SessionLocal()
    outcome: Counter = Counter()
    per_file = {}
    started = time.perf_counter()
    try:
        for path in files:
            counts: Counter = Counter()
            for raw in read_jsonl(path):
                result = ingest_document(
                    db,
                    DocumentIn(
                        title=raw["title"], text=raw["text"], kb=raw["kb"], url=raw.get("url"),
                        source_type=raw.get("source_type"), publisher=raw.get("publisher"),
                        published_at=_date(raw.get("published_at")),
                        licence_note=raw.get("licence_note"), attribution=raw.get("attribution"),
                        category=raw.get("category"), adapter=raw.get("adapter"),
                    ),
                    min_words=40,
                )
                counts[result.status] += 1
                counts["chunks"] += result.chunks
                if result.status == "rejected":
                    print(f"  rejected {raw['title'][:60]!r}: {result.reason}")
                db.commit()
            per_file[path.stem] = dict(counts)
            outcome.update(counts)
            print(f"{path.stem:12} created {counts['created']:4}  duplicate {counts['duplicate']:4}  "
                  f"rejected {counts['rejected']:3}  chunks {counts['chunks']:5}", flush=True)

        totals = {
            kb: {
                "sources": db.scalar(select(func.count()).select_from(ResearchSource).where(ResearchSource.kb == kb)),
                "chunks": db.scalar(select(func.count()).select_from(ResearchChunk).where(ResearchChunk.kb == kb)),
            }
            for kb in ("A", "B")
        }
        by_type = dict(
            db.execute(
                select(ResearchSource.source_type, func.count())
                .where(ResearchSource.kb.in_(("A", "B")))
                .group_by(ResearchSource.source_type)
            ).all()
        )
    finally:
        db.close()

    MANIFEST.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "embedding_model": get_embedder().model_name,
        "files": per_file,
        "knowledge_bases": totals,
        "sources_by_type": by_type,
    }, indent=2), encoding="utf-8")
    print(f"\nthis run: {dict(outcome)} in {time.perf_counter() - started:.0f}s")
    print(f"KB totals: {totals}")


if __name__ == "__main__":
    main()
