"""Build the labelled classification set used by ``scripts/run_eval.py``.

Sources:
1. ``data/test_ideas/sample_ideas.md``: the 10 hand-written Phase 0 ideas.
2. ``10 sample datasets/business-ideas-dataset-main``: 42 real idea pitches (MIT).
   Their own category (App, SaaS, Tool, ...) is mapped to Ideaform categories.
   Product ideas are labelled ``software`` but ``business`` is also accepted,
   because a pitched product is a venture as much as an application.

Writes ``data/eval/classification_labels.csv``. Standard library only:

    python scripts/build_eval_set.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "test_ideas" / "sample_ideas.md"
IDEAS_CSV = (
    ROOT
    / "10 sample datasets"
    / "business-ideas-dataset-main"
    / "business-ideas-dataset-main"
    / "data"
    / "ideas.csv"
)
OUT = ROOT / "data" / "eval" / "classification_labels.csv"

# dataset category -> (expected, also acceptable)
CATEGORY_MAP = {
    "SaaS": ("software", "business"),
    "App": ("software", "business"),
    "Mobile App": ("software", "business"),
    "Tool": ("software", "business"),
    "Platform": ("business", "software"),
    "SaaS + Hardware": ("technology", "software"),
}

ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")


def sample_rows() -> list[dict]:
    rows = []
    for line in SAMPLES.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match:
            continue
        number, category, idea, expected_reqs = match.groups()
        rows.append(
            {
                "id": f"sample-{number}",
                "source": "data/test_ideas/sample_ideas.md",
                "idea_text": idea,
                # the vague idea has no right category; it is judged on confidence
                "expected_category": "" if category == "vague" else category,
                "also_acceptable": "",
                "expect_low_confidence": "true" if category == "vague" else "false",
                "notes": expected_reqs,
            }
        )
    return rows


def dataset_rows() -> list[dict]:
    rows = []
    with IDEAS_CSV.open(encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            expected, alt = CATEGORY_MAP.get(item["category"], ("software", "business"))
            rows.append(
                {
                    "id": f"bidb-{item['slug']}",
                    "source": "business-ideas-dataset (MIT)",
                    "idea_text": f"{item['title']}. {item['pitch']}",
                    "expected_category": expected,
                    "also_acceptable": alt,
                    "expect_low_confidence": "false",
                    "notes": f"dataset category: {item['category']}; "
                    f"competitors: {item['competitor_names'].replace('|', ', ')}",
                }
            )
    return rows


def main() -> None:
    rows = sample_rows() + dataset_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} labelled ideas -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
