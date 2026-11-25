"""Phase 2 gate: research every sample idea and check its evidence.

For each project of the demo account (``scripts/seed_demo.py``): run understanding
(Groq) if needed, run the Research Agent (Tavily + scraper into KB-C), then ask
three questions per idea with hybrid retrieval and check that passages come back
with source links that open. Writes ``data/eval/results/sample_research_<ts>.md``.

    backend/.venv/Scripts/python scripts/research_sample_ideas.py [--limit 3]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "eval" / "results"
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.project import Project, ProjectVersion  # noqa: E402
from app.models.research import ResearchSource  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.knowledge.retrieval import Scope, search  # noqa: E402
from app.services.nlp.pipeline import run_understanding  # noqa: E402
from app.services.research.agent import run_research  # noqa: E402

DEMO_EMAIL = "demo@example.com"


def questions(title: str, structured: dict) -> list[str]:
    feature = (structured.get("key_features") or ["the product"])[0]
    users = (structured.get("target_users") or ["customers"])[0]
    return [
        f"Who are the competitors of {title.split(':', 1)[-1].strip()}?",
        f"How do similar products price {feature}?",
        f"What do {users} need and what problems do they have?",
    ]


def link_ok(url: str) -> bool:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True,
                      headers={"User-Agent": "IdeaformBot/1.0 (link check)"})
        return r.status_code < 400
    except httpx.HTTPError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    db = SessionLocal()
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        raise SystemExit("Run scripts/seed_demo.py first.")
    projects = list(db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.title)))
    projects.sort(key=lambda p: int(p.title.split()[1].rstrip(":")) if p.title.startswith("Sample") else 99)
    if args.limit:
        projects = projects[: args.limit]

    rows = []
    for project in projects:
        print(f"\n== {project.title}", flush=True)
        version = db.get(ProjectVersion, project.current_version_id)
        if not version.structured_idea:
            try:
                run_understanding(db, project.id)
            except Exception as exc:  # noqa: BLE001
                print(f"   understanding failed: {exc}")
            db.refresh(version)
        started = time.perf_counter()
        try:
            summary = run_research(db, project.id)
            error = ""
        except Exception as exc:  # noqa: BLE001
            summary, error = {}, str(exc)[:200]
        took = time.perf_counter() - started
        n_sources = len(list(db.scalars(select(ResearchSource.id).where(ResearchSource.project_id == project.id))))

        answered, cited_urls = 0, []
        for q in questions(project.title, version.structured_idea or {}):
            passages = search(db, q, scope=Scope(user.id, project.id), k=5)
            if passages:
                answered += 1
                cited_urls += [p.url for p in passages[:2] if p.url and p.url.startswith("http")]
        cited_urls = list(dict.fromkeys(cited_urls))[:6]
        working = sum(link_ok(u) for u in cited_urls)
        row = {
            "title": project.title,
            "category": project.category,
            "queries": len(summary.get("queries", [])),
            "fetched": summary.get("pages_fetched", 0),
            "stored": summary.get("pages_stored", 0),
            "robots": summary.get("pages_skipped_robots", 0),
            "sources": n_sources,
            "answered": answered,
            "links": f"{working}/{len(cited_urls)}",
            "seconds": round(took),
            "unanswered": len(summary.get("unanswered_questions", [])),
            "error": error,
        }
        rows.append(row)
        print("   ", row, flush=True)
    db.close()

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"sample_research_{datetime.now():%Y%m%d_%H%M%S}.md"
    lines = [
        f"# Research on the sample ideas ({datetime.now():%Y-%m-%d %H:%M})", "",
        "Each idea: Research Agent run (Tavily discovery + own scraper into KB-C), then 3 hybrid-search "
        "questions (competitors, pricing, user needs). Links = cited source URLs that open (HTTP < 400).", "",
        "| Idea | Category | Queries | Fetched | Stored | Robots-skipped | KB-C sources | Questions answered | Links open | Time (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['title']} | {r['category']} | {r['queries']} | {r['fetched']} | {r['stored']} | {r['robots']} "
            f"| {r['sources']} | {r['answered']}/3 | {r['links']} | {r['seconds']} |"
            + (f" error: {r['error']}" if r["error"] else "")
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / "sample_research_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n-> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
