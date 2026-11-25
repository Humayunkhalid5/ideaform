"""Add your own notes, downloaded PDFs and the sample datasets to the KB seed corpus.

Reads:
* ``rag/*.md``: the team's curated notes (KB-A business guides, KB-B technical guides);
* ``data/knowledge_seed/documents/`` (any PDF, DOCX, TXT or MD you drop there),
  with an optional ``documents/sources.json`` giving title/url/licence per file;
* ``data/knowledge_seed/datasets_catalogue.json`` + ``10 sample datasets/``: one
  descriptive document per dataset (columns, size, summary statistics), so retrieval
  can point to the datasets as evidence.

Writes ``data/scraped_corpus/kb_seed/notes.jsonl``, ``documents.jsonl`` and
``datasets.jsonl``; load them with ``ingest.py``.

    backend/.venv/Scripts/python scripts/seed_kb/add_documents.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, doc, use_backend, write_jsonl  # noqa: E402

use_backend()

from app.services.knowledge.loaders import UnsupportedDocument, load_file  # noqa: E402

csv.field_size_limit(2**31 - 1)

RAG_DIR = ROOT / "rag"
DOCS_DIR = ROOT / "data" / "knowledge_seed" / "documents"
CATALOGUE = ROOT / "data" / "knowledge_seed" / "datasets_catalogue.json"

# rag notes: file prefix -> (kb, category)
NOTE_KB = {
    "01": ("A", "business"), "02": ("A", "business"), "03": ("A", "business"),
    "04": ("A", "business"), "05": ("B", "software"), "06": ("B", "software"),
    "07": ("A", "business"),
}


def notes() -> list[dict]:
    out = []
    for path in sorted(RAG_DIR.glob("*.md")):
        kb, category = NOTE_KB.get(path.name[:2], ("A", "business"))
        loaded = load_file(path.read_bytes(), path.name)
        out.append(doc(
            title=loaded.title, text=loaded.text, url=f"rag/{path.name}", kb=kb,
            source_type="note", publisher="Ideaform team notes",
            licence_note="Team-authored notes (internal): free to use within the project",
            attribution="Ideaform project team", category=category, adapter="note",
        ))
    return out


def documents() -> list[dict]:
    if not DOCS_DIR.exists():
        return []
    meta = {}
    meta_file = DOCS_DIR / "sources.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    out = []
    for path in sorted(DOCS_DIR.iterdir()):
        if path.name == "sources.json" or path.is_dir():
            continue
        try:
            loaded = load_file(path.read_bytes(), path.name)
        except UnsupportedDocument as exc:
            print(f"  skipped {path.name}: {exc}")
            continue
        m = meta.get(path.name, {})
        out.append(doc(
            title=m.get("title") or loaded.title, text=loaded.text, url=m.get("url"),
            kb=m.get("kb", "A"), source_type=m.get("source_type", "report"),
            publisher=m.get("publisher", "Downloaded document"),
            licence_note=m.get("licence", "Downloaded for study: cite and link, check reuse terms"),
            attribution=m.get("attribution", m.get("publisher", path.name)),
            category=m.get("category", "business"), adapter="document",
            published_at=m.get("published_at"),
        ))
    return out


def _numeric_summary(path: Path, columns: list[str], max_rows: int = 200_000) -> list[str]:
    values: dict[str, list[float]] = {c: [] for c in columns}
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for i, row in enumerate(csv.DictReader(handle)):
            if i >= max_rows:
                break
            for col in columns:
                raw = (row.get(col) or "").replace(",", "").replace("$", "").replace("%", "").strip()
                try:
                    values[col].append(float(raw))
                except ValueError:
                    pass
    lines = []
    for col, nums in values.items():
        if len(nums) >= 5:
            lines.append(
                f"{col}: mean {statistics.fmean(nums):,.2f}, median {statistics.median(nums):,.2f}, "
                f"min {min(nums):,.2f}, max {max(nums):,.2f} (n={len(nums):,})"
            )
    return lines[:12]


def _sample_rows(path: Path, n: int = 5) -> list[str]:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for i, row in enumerate(reader):
            if i >= n:
                break
            cells = [f"{k}={v}" for k, v in list(row.items())[:8] if k and v]
            rows.append("; ".join(cells)[:400])
    return rows


def datasets() -> list[dict]:
    if not CATALOGUE.exists():
        print("  datasets: run scripts/profile_datasets.py first")
        return []
    out = []
    for entry in json.loads(CATALOGUE.read_text(encoding="utf-8")):
        parts = [
            f"Dataset: {entry['title']}. Ideaform category: {entry['category']}. "
            f"Intended use: {entry.get('use', '')}. Licence: {entry.get('licence', 'unknown')}."
        ]
        for f in entry["files"]:
            path = ROOT / f["path"]
            parts.append(
                f"File {Path(f['path']).name}: {f['rows']:,} rows, {f['size_kb']:,} KB. "
                f"Columns: {', '.join(f['columns'][:40])}."
            )
            if path.exists():
                stats = _numeric_summary(path, f["columns"][:40])
                if stats:
                    parts.append("Numeric summary: " + "; ".join(stats) + ".")
                samples = _sample_rows(path, 3)
                if samples:
                    parts.append("Example rows: " + " | ".join(samples))
        kb = entry.get("kb", "A")
        category = entry["category"] if entry["category"] in ("business", "software", "technology") else "software"
        out.append(doc(
            title=f"Dataset: {entry['title']}", text="\n\n".join(parts),
            url=f"10 sample datasets/{entry['folder']}", kb=kb, source_type="dataset",
            publisher="10 sample datasets (project data)",
            licence_note=f"Dataset licence: {entry.get('licence', 'unknown')}",
            attribution=entry.get("attribution") or entry["title"], category=category,
            adapter="dataset",
        ))
    return out


def main() -> None:
    for name, fn in (("notes", notes), ("documents", documents), ("datasets", datasets)):
        docs = fn()
        path = write_jsonl(name, docs)
        print(f"{name}: {len(docs)} documents -> {path.name}")


if __name__ == "__main__":
    main()
