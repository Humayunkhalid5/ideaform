"""Phase 3 gate without a database: evaluate a sample idea, improve it, compare.

Runs the real Evaluation Agent calls against Groq (GROQ_API_KEY from .env), but takes
evidence from the curated ``rag/`` notes (ranked by keyword overlap) instead of the
PostgreSQL knowledge base, so it works on a machine without the database.

    backend/.venv/Scripts/python scripts/phase3_offline_demo.py [--idea 4] [--accept 2]

Writes the full before/after record to ``data/eval/results/phase3_offline_demo.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.evaluation import Evaluation, EvaluationDimension  # noqa: E402
from app.models.project import ProjectVersion  # noqa: E402
from app.services.evaluation import evaluator  # noqa: E402
from app.services.evaluation.compare import compare  # noqa: E402
from app.services.evaluation.evidence import (  # noqa: E402
    build_queries,
    number_passages,
    validate_dimension,
    validate_ids_on,
)
from app.services.knowledge.retrieval import Passage, keyword_terms  # noqa: E402
from app.services.llm import get_llm  # noqa: E402
from app.services.nlp.extraction import extract_idea  # noqa: E402

SAMPLES = ROOT / "data" / "test_ideas" / "sample_ideas.md"
OUT = ROOT / "data" / "eval" / "results" / "phase3_offline_demo.json"


def sample_idea(number: int) -> str:
    for line in SAMPLES.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == str(number):
            return cells[2]
    raise SystemExit(f"No sample idea #{number}")


def rag_chunks(words_per_chunk: int = 220) -> list[Passage]:
    chunks = []
    for path in sorted((ROOT / "rag").glob("*.md")):
        words = path.read_text(encoding="utf-8").split()
        source_id = uuid.uuid5(uuid.NAMESPACE_URL, path.name)
        for i in range(0, len(words), words_per_chunk):
            chunks.append(
                Passage(
                    chunk_id=uuid.uuid5(source_id, str(i)),
                    source_id=source_id,
                    kb="A",
                    content=" ".join(words[i : i + words_per_chunk]),
                    title=path.stem.replace("_", " "),
                    url=None,
                    publisher="Ideaform curated notes (rag/)",
                    source_type="notes",
                    published_at=None,
                    retrieved_at=datetime.now(timezone.utc),
                    licence_note="Project-authored",
                    restricted=False,
                    chunk_index=i // words_per_chunk,
                )
            )
    return chunks


def offline_evidence(title: str, structured: dict, idea_text: str, chunks: list[Passage]):
    results = {}
    for key, (query, _kbs) in build_queries(title, structured, idea_text).items():
        terms = set(keyword_terms(query, limit=20))
        ranked = sorted(
            chunks, key=lambda c: len(terms & set(keyword_terms(c.content, limit=400))), reverse=True
        )
        results[key] = ranked[:4]
    return number_passages(results)


def run_once(provider, title, idea_text, chunks, baseline=None):
    structured, _ = extract_idea(idea_text, "software")
    structured = structured.model_dump()
    evidence = offline_evidence(title, structured, idea_text, chunks)
    draft = evaluator.evaluate(
        provider, title=title, structured=structured, idea_text=idea_text,
        evidence=evidence, baseline=baseline,
    )
    notes = []
    for dim in draft.dimensions:
        notes += validate_dimension(dim, evidence)
    validate_ids_on(draft.critique.risks, evidence)
    validate_ids_on(draft.critique.improvements, evidence)
    validate_ids_on(draft.competitors, evidence)
    return structured, evidence, draft, notes


def to_rows(draft, version_no, idea_text, baseline=None, baseline_eval=None):
    version = ProjectVersion(id=uuid.uuid4(), version_no=version_no, idea_text=idea_text)
    evaluation = Evaluation(
        id=uuid.uuid4(),
        version_id=version.id,
        overall_score=round(sum(d.score for d in draft.dimensions) / 6),
        risks=[r.model_dump() for r in draft.critique.risks],
        baseline_evaluation_id=baseline_eval.id if baseline_eval else None,
    )
    for d in draft.dimensions:
        prev = baseline.dimensions.get(d.dimension) if baseline else None
        reason = d.change_reason or (evaluator.fallback_change_reason(prev, d) if prev else None)
        evaluation.dimensions.append(
            EvaluationDimension(
                dimension=d.dimension, score=d.score, confidence=d.confidence,
                explanation=d.explanation, change_reason=reason,
                previous_score=prev["score"] if prev else None,
            )
        )
    return version, evaluation


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idea", type=int, default=4, help="row number in sample_ideas.md")
    parser.add_argument("--accept", type=int, default=2, help="improvements to accept")
    args = parser.parse_args()

    provider = get_llm()
    chunks = rag_chunks()
    idea_text = sample_idea(args.idea)
    title = f"Sample idea {args.idea}"
    print(f"Idea v1: {idea_text}\n")

    _, ev1, draft1, notes1 = run_once(provider, title, idea_text, chunks)
    print(f"v1 evaluation ({draft1.usage.calls} calls, {len(ev1.items)} passages)")
    for d in draft1.dimensions:
        labels = {c.label for c in d.claims}
        print(f"  {d.dimension:22} {d.score:3}  {d.confidence:6}  cites {d.evidence_ids}  labels {sorted(labels)}")
    print(f"  risks {len(draft1.critique.risks)}, improvements {len(draft1.critique.improvements)}, "
          f"competitors {len(draft1.competitors)}, notes {len(notes1)}")

    accepted = [
        {"title": i.title, "change": i.change or i.title} for i in draft1.critique.improvements[: args.accept]
    ]
    rewritten, _ = evaluator.rewrite_idea(
        provider, title=title, idea_text=idea_text, changes=accepted, note=None
    )
    print(f"\nAccepted: {[c['title'] for c in accepted]}\nIdea v2: {rewritten.idea_text}\n")

    v1, e1 = to_rows(draft1, 1, idea_text)
    baseline = evaluator.Baseline(
        version_no=1, idea_text=idea_text,
        dimensions={d.dimension: {"score": d.score, "confidence": d.confidence, "explanation": d.explanation}
                    for d in draft1.dimensions},
    )
    _, ev2, draft2, notes2 = run_once(provider, title, rewritten.idea_text, chunks, baseline)
    v2, e2 = to_rows(draft2, 2, rewritten.idea_text, baseline, e1)

    result = compare(e1, e2, v1, v2, [], [])
    print(result["summary"])
    for row in result["dimensions"]:
        print(f"  {row['label']:22} {row['score_a']:3} -> {row['score_b']:3} ({row['delta']:+d})  {row['reason']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "idea_v1": idea_text,
                "idea_v2": rewritten.idea_text,
                "accepted": accepted,
                "evaluation_v1": {
                    "summary": draft1.summary,
                    "dimensions": [d.model_dump() for d in draft1.dimensions],
                    "critique": draft1.critique.model_dump(),
                    "competitors": [c.model_dump() for c in draft1.competitors],
                    "business_model": draft1.business_model.model_dump() if draft1.business_model else None,
                    "validation_notes": notes1,
                    "evidence": ev1.catalogue(),
                },
                "evaluation_v2": {
                    "summary": draft2.summary,
                    "dimensions": [d.model_dump() for d in draft2.dimensions],
                    "validation_notes": notes2,
                },
                "comparison": {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in result.items()},
                "tokens": {
                    "v1": draft1.usage.tokens_in + draft1.usage.tokens_out,
                    "v2": draft2.usage.tokens_in + draft2.usage.tokens_out,
                },
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
