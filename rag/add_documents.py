#!/usr/bin/env python3
"""
Add your own documents (.md, .txt, .pdf, .docx) to the VentureAI knowledge base.

Converts every supported file in a folder into the same JSONL format that
collect.py writes, so ingest.py can load them. Duplicates are skipped.

Optional front matter at the top of .md/.txt files overrides the defaults:
---
title: Business model patterns
kb: A                      (A = business, B = technical)
category: business models
url: https://source-or-local-reference
licence: Original team notes
published_at: 2026-01-15
---

Usage:
  python add_documents.py --folder manual_docs --kb A --licence "Original team notes"
  python add_documents.py --folder downloads --kb A --url-prefix "https://example.org/reports/" \
      --licence "Open access; cite the report"
Then run: python ingest.py
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT_PATH = Path(os.getenv("KB_OUT", "data/knowledge_seed/documents.jsonl"))


def parse_front_matter(text):
    meta = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            text = parts[2]
    return meta, text.strip()


def read_file(path):
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--kb", choices=["A", "B"], default="A")
    ap.add_argument("--category", default="manual document")
    ap.add_argument("--licence", default="Check and record the licence for this document")
    ap.add_argument("--url-prefix", default="", help="optional URL base to build source links")
    args = ap.parse_args()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if OUT_PATH.exists():
        for line in OUT_PATH.open(encoding="utf-8"):
            try:
                seen.add(json.loads(line)["content_hash"])
            except (json.JSONDecodeError, KeyError):
                pass

    added = 0
    with OUT_PATH.open("a", encoding="utf-8") as out:
        for path in sorted(Path(args.folder).rglob("*")):
            if not path.is_file():
                continue
            try:
                raw = read_file(path)
            except Exception as e:  # noqa: BLE001
                print(f"failed {path.name}: {e}", file=sys.stderr)
                continue
            if raw is None:
                continue
            meta, body = parse_front_matter(raw)
            if len(body) < 300:
                print(f"skipped (too short or empty text): {path.name}", file=sys.stderr)
                continue
            doc = {
                "kb": meta.get("kb", args.kb),
                "title": meta.get("title", path.stem.replace("_", " ")),
                "url": meta.get("url") or (args.url_prefix + path.name if args.url_prefix else f"file://{path.name}"),
                "source_type": "manual_document",
                "category": meta.get("category", args.category),
                "published_at": meta.get("published_at"),
                "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "licence_note": meta.get("licence", args.licence),
                "content": body,
                "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            }
            if doc["content_hash"] in seen:
                continue
            seen.add(doc["content_hash"])
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")
            added += 1
            print(f"added: {doc['title']} [{doc['kb']}]")
    print(f"\n{added} new documents written to {OUT_PATH}. Now run: python ingest.py")


if __name__ == "__main__":
    main()
