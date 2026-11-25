"""Classification accuracy on the labelled set (AI_DESIGN.md section 10).

Calls the real Groq model for each idea in ``data/eval/classification_labels.csv``
and writes ``data/eval/results/classification_<timestamp>.csv`` plus a summary with
accuracy, latency and token use. Needs ``GROQ_API_KEY`` in ``.env``.

Run with the backend virtualenv, from the repo root:

    backend/.venv/Scripts/python scripts/run_eval.py --limit 10
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
LABELS = ROOT / "data" / "eval" / "classification_labels.csv"
RESULTS = ROOT / "data" / "eval" / "results"

sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # settings read ../.env and .env relative to backend/


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=0, help="only the first N ideas")
    args = parser.parse_args()

    from app.config import get_settings
    from app.services.llm.base import LLMError
    from app.services.nlp.extraction import classify_idea

    if not get_settings().groq_api_key:
        raise SystemExit("GROQ_API_KEY is not set in .env; nothing to evaluate.")

    with LABELS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if args.limit:
        rows = rows[: args.limit]

    results, correct, judged, tokens, latency = [], 0, 0, 0, 0
    for row in rows:
        started = time.perf_counter()
        try:
            label, call = classify_idea(row["idea_text"])
            predicted, confidence, error = label.category, label.confidence, ""
            tokens += call.tokens_in + call.tokens_out
        except LLMError as exc:
            predicted, confidence, error = "", "", str(exc)[:200]
        elapsed = int((time.perf_counter() - started) * 1000)
        latency += elapsed

        if row["expect_low_confidence"] == "true":
            ok = confidence == "low"
        else:
            allowed = {row["expected_category"], *filter(None, [row["also_acceptable"]])}
            ok = predicted in allowed
        judged += 1
        correct += ok
        results.append({**row, "predicted": predicted, "confidence": confidence,
                        "correct": ok, "latency_ms": elapsed, "error": error})
        print(f"{'OK ' if ok else 'BAD'} {row['id']:<40} {predicted or error}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"classification_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    print(
        f"\naccuracy {correct}/{judged} = {correct / max(judged, 1):.0%}, "
        f"avg latency {latency // max(judged, 1)} ms, tokens {tokens:,}\n-> {out.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
