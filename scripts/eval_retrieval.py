"""Retrieval comparison on the labelled query set (AI_DESIGN 10.2 / 10.3 experiment 1).

Runs every query in ``data/eval/retrieval_queries.json`` against the shared KB-A/B
in four modes: keyword-only, vector-only, hybrid (RRF) and hybrid + rerank, and
reports Precision@5, Recall@10, MRR and nDCG@10. A passage counts as relevant when
its source URL contains one of the query's labelled substrings.

    backend/.venv/Scripts/python scripts/eval_retrieval.py
Writes ``data/eval/results/retrieval_<timestamp>.json`` and ``.md``.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "data" / "eval" / "retrieval_queries.json"
RESULTS = ROOT / "data" / "eval" / "results"

sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from app.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.knowledge import retrieval  # noqa: E402

MODES = [
    ("keyword", dict(mode="keyword", rerank=False)),
    ("vector", dict(mode="vector", rerank=False)),
    ("hybrid", dict(mode="hybrid", rerank=False)),
    ("hybrid+rerank", dict(mode="hybrid", rerank=True)),
]


def is_relevant(url: str | None, labels: list[str]) -> str | None:
    if not url:
        return None
    return next((label for label in labels if label.lower() in url.lower()), None)


def score(passages, labels: list[str]) -> dict:
    hits = [is_relevant(p.url, labels) for p in passages]
    p5 = sum(1 for h in hits[:5] if h) / 5
    found = {h for h in hits[:10] if h}
    r10 = len(found) / len(labels)
    rr = next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    dcg = sum(1 / math.log2(i + 2) for i, h in enumerate(hits[:10]) if h)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(labels) * 3)))
    return {"p@5": p5, "r@10": r10, "mrr": rr, "ndcg@10": dcg / ideal if ideal else 0.0}


def main() -> None:
    settings = get_settings()
    # one passage per source would hide multi-passage hits; allow a few per source
    labelled = json.loads(QUERIES.read_text(encoding="utf-8"))["queries"]
    db = SessionLocal()
    table: dict[str, dict[str, float]] = {}
    per_query: dict[str, dict] = {}
    timings: dict[str, float] = {}
    try:
        for name, opts in MODES:
            totals = {"p@5": 0.0, "r@10": 0.0, "mrr": 0.0, "ndcg@10": 0.0}
            started = time.perf_counter()
            for q in labelled:
                passages = retrieval.search(
                    db, q["query"], scope=retrieval.Scope(), k=10, **opts
                )
                s = score(passages, q["relevant"])
                per_query.setdefault(q["id"], {"query": q["query"]})[name] = s
                for key in totals:
                    totals[key] += s[key]
            timings[name] = (time.perf_counter() - started) / len(labelled) * 1000
            table[name] = {k: round(v / len(labelled), 3) for k, v in totals.items()}
            print(f"{name:14} " + "  ".join(f"{k} {v:.3f}" for k, v in table[name].items())
                  + f"  ({timings[name]:.0f} ms/query)", flush=True)
    finally:
        db.close()

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = {
        "queries": len(labelled),
        "embedding_model": settings.embedding_model,
        "reranker_model": settings.reranker_model,
        "semantic_k": settings.retrieval_semantic_k,
        "keyword_k": settings.retrieval_keyword_k,
        "max_per_source": settings.retrieval_max_per_source,
    }
    (RESULTS / f"retrieval_{stamp}.json").write_text(
        json.dumps({"meta": meta, "summary": table, "ms_per_query": timings, "per_query": per_query}, indent=2),
        encoding="utf-8",
    )
    lines = [
        f"# Retrieval comparison ({len(labelled)} labelled queries, KB-A + KB-B)",
        "",
        "| Mode | Precision@5 | Recall@10 | MRR | nDCG@10 | ms/query |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, row in table.items():
        lines.append(f"| {name} | {row['p@5']:.3f} | {row['r@10']:.3f} | {row['mrr']:.3f} | "
                     f"{row['ndcg@10']:.3f} | {timings[name]:.0f} |")
    lines += ["", f"Models: {settings.embedding_model} (vectors), {settings.reranker_model} (reranker).",
              f"Generated {datetime.now():%Y-%m-%d %H:%M} by scripts/eval_retrieval.py."]
    (RESULTS / f"retrieval_{stamp}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / "retrieval_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name in ("hybrid", "hybrid+rerank"):
        wins = [k for k in table[name] if table[name][k] > table["vector"][k]]
        print(f"{name} beats vector-only on: {', '.join(wins) or 'nothing'}")


if __name__ == "__main__":
    main()
