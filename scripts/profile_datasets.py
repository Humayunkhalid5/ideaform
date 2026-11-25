"""Profile the "10 sample datasets" folder into a dataset catalogue.

Writes ``data/knowledge_seed/datasets_catalogue.json`` and ``.md``: one entry per
dataset with its Ideaform category, files, row counts, columns, size, licence
status and intended use. The catalogue is the "Dataset and resources list"
deliverable and the input for Phase 2 ingestion (KB-A business, KB-B technical).

Standard library only. Usage (from the repo root):

    python scripts/profile_datasets.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "10 sample datasets"
OUT_DIR = ROOT / "data" / "knowledge_seed"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Curated by hand: what each folder is, which Ideaform category it supports and how
# it will be used. Licences are recorded only where the dataset ships one.
META: dict[str, dict] = {
    "business-ideas-dataset-main": {
        "title": "Business Ideas Dataset (businessideasdb.com)",
        "category": "business",
        "kb": "A",
        "licence": "MIT (LICENSE file in the folder)",
        "attribution": "businessideasdb.com business-ideas-dataset",
        "use": "Labelled idea texts for the classification eval set (data/eval); "
        "competitor names and scores as KB-A market signals.",
    },
    "e commerce": {
        "title": "E-commerce sales reports (Amazon India, pricing, P&L)",
        "category": "business",
        "kb": "A",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Pricing, order and channel statistics for market and business-model evidence.",
    },
    "sass dataset": {
        "title": "Top 100 SaaS companies 2025",
        "category": "software",
        "kb": "A",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Competitor and benchmark facts (ARR, funding, product) for software ideas.",
    },
    "startup": {
        "title": "Startup success/failure records (US, Crunchbase-style)",
        "category": "business",
        "kb": "A",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Funding rounds, milestones and outcomes as risk and success signals.",
    },
    "startup funding_sass": {
        "title": "Indian startup funding rounds",
        "category": "business",
        "kb": "A",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Funding amounts per industry and city for market-opportunity evidence.",
    },
    "student discount and price_sass": {
        "title": "Student software pricing and discounts",
        "category": "software",
        "kb": "A",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Price points for student-focused ideas (e.g. the demo tutor idea).",
    },
    "tech_1": {
        "title": "IoT environmental telemetry (sensor readings)",
        "category": "technology",
        "kb": "B",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Example sensor data rates and fields for IoT technology ideas "
        "(sample idea 7, water-leak sensors).",
    },
    "tech_2": {
        "title": "Humanoid robots 2026 catalogue and hardware specs",
        "category": "technology",
        "kb": "B",
        "licence": "unknown: confirm the original source before redistribution",
        "use": "Hardware specs and manufacturer facts for robotics/hardware ideas.",
    },
    "tech_3": {
        "title": "Steel trading ERP sample (products, suppliers, invoices, inventory)",
        "category": "software",
        "kb": "B",
        "licence": "unknown: synthetic-looking ERP data; confirm before redistribution",
        "use": "Reference schema for generated database designs of ERP/inventory ideas.",
    },
    "vague": {
        "title": "GitHub AI repositories 2026",
        "category": "vague",
        "kb": "B",
        "licence": "unknown: repository metadata from GitHub; check each repo's licence column",
        "use": "Landscape of AI projects for vague 'something with AI' ideas: shows "
        "crowded areas and helps ask clarifying questions.",
    },
}


def _profile_csv(path: Path) -> dict:
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        rows = sum(1 for _ in reader)
    columns = [c.strip() for c in header if c.strip() and not c.startswith("Unnamed")]
    return {"rows": rows, "columns": columns}


def profile() -> list[dict]:
    if not DATASETS.exists():
        raise SystemExit(f"Not found: {DATASETS}")

    catalogue = []
    for folder in sorted(p for p in DATASETS.iterdir() if p.is_dir()):
        meta = META.get(folder.name, {"title": folder.name, "category": "unknown"})
        files = []
        for path in sorted(folder.rglob("*.csv")):
            info = _profile_csv(path)
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "size_kb": round(path.stat().st_size / 1024, 1),
                    **info,
                }
            )
        catalogue.append({"folder": folder.name, **meta, "files": files})
    return catalogue


def _markdown(catalogue: list[dict]) -> str:
    lines = [
        "# Dataset catalogue",
        "",
        "Generated by `scripts/profile_datasets.py` from `10 sample datasets/`. "
        "Do not edit by hand; re-run the script.",
        "",
        "| Dataset | Category | KB | Files | Rows | Licence | Use |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for d in catalogue:
        rows = sum(f["rows"] for f in d["files"])
        lines.append(
            f"| {d['title']} | {d['category']} | {d.get('kb', '-')} | {len(d['files'])} "
            f"| {rows:,} | {d.get('licence', '-')} | {d.get('use', '-')} |"
        )
    lines += ["", "## Files", ""]
    for d in catalogue:
        lines.append(f"### {d['title']}")
        lines.append("")
        for f in d["files"]:
            cols = ", ".join(f["columns"][:12]) + (" …" if len(f["columns"]) > 12 else "")
            lines.append(f"- `{f['path']}`: {f['rows']:,} rows, {f['size_kb']:,} KB. Columns: {cols}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    catalogue = profile()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "datasets_catalogue.json").write_text(
        json.dumps(catalogue, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "datasets_catalogue.md").write_text(_markdown(catalogue), encoding="utf-8")
    total = sum(f["rows"] for d in catalogue for f in d["files"])
    print(f"{len(catalogue)} datasets, {total:,} rows -> {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
