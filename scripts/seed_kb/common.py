"""Shared helpers for the KB seeding scripts (collect.py, add_documents.py, ingest.py).

Collected documents are written as JSON Lines, one normalised document per line:
``title, text, url, kb, source_type, publisher, published_at, licence_note,
attribution, category, adapter`` (the same shape as ``DocumentIn``).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
COLLECTED = ROOT / "data" / "scraped_corpus" / "kb_seed"  # git-ignored corpus
MANIFEST = ROOT / "data" / "knowledge_seed" / "kb_manifest.json"  # committed summary

def use_backend() -> None:
    """Import the backend package and its .env from any working directory."""
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)


def write_jsonl(name: str, docs: list[dict]) -> Path:
    COLLECTED.mkdir(parents=True, exist_ok=True)
    path = COLLECTED / f"{name}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for doc in docs:
            handle.write(json.dumps(doc, ensure_ascii=False, default=str) + "\n")
    return path


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def doc(
    *,
    title: str,
    text: str,
    url: str | None,
    kb: str,
    source_type: str,
    publisher: str,
    licence_note: str,
    attribution: str,
    category: str,
    adapter: str,
    published_at: str | None = None,
) -> dict:
    return {
        "title": title.strip()[:300],
        "text": text,
        "url": url,
        "kb": kb,
        "source_type": source_type,
        "publisher": publisher,
        "published_at": published_at,
        "licence_note": licence_note,
        "attribution": attribution,
        "category": category,
        "adapter": adapter,
    }
