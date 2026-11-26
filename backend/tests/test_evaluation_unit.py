"""Phase 3 logic that needs no database: schemas, evidence rules, agent calls, comparison."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx

from app.models.evaluation import DIMENSIONS, Evaluation, EvaluationDimension
from app.models.project import ProjectRequirement, ProjectVersion
from app.schemas.evaluation import Claim, DimensionResult, Improvement, Risk, normalise_ids
from app.services.evaluation import evaluator
from app.services.evaluation.agent import evidence_label, verify_website
from app.services.evaluation.compare import compare, diff_lists, text_diff
from app.services.evaluation.evidence import (
    build_queries,
    format_block,
    number_passages,
    validate_dimension,
)
from app.services.knowledge.retrieval import Passage
from app.services.llm.groq import _retry_after
from tests.evaluation_fakes import SCORES, FakeEvalProvider


def _passage(n: int, source: uuid.UUID | None = None, content: str | None = None) -> Passage:
    return Passage(
        chunk_id=uuid.uuid4(), source_id=source or uuid.uuid4(), kb="A",
        content=content or f"Passage {n} about affordable tutors for students.",
        title=f"Source {n}", url=f"https://site{n}.example/page", publisher=None,
        source_type="web", published_at=None, retrieved_at=datetime.now(timezone.utc),
        licence_note=None, restricted=False, chunk_index=0,
    )


def _evidence(n_sources: int = 4):
    shared = _passage(0)
    results = {d: [shared] + [_passage(i) for i in range(1, n_sources)] for d in DIMENSIONS}
    results["risks"] = [_passage(9)]
    return number_passages(results)


# ------------------------------------------------------------------ schemas


def test_schema_normalises_model_drift():
    dim = DimensionResult.model_validate({
        "dimension": "Market Opportunity", "score": "6.5", "confidence": "Moderate",
        "explanation": "x", "evidence_ids": "E1, [e3]", "assumptions": "only one",
    })
    assert dim.dimension == "market_opportunity"
    assert dim.score == 65 and dim.confidence == "medium"
    assert dim.evidence_ids == ["E1", "E3"] and dim.assumptions == ["only one"]
    assert normalise_ids([2, "[E2]", "E10"]) == ["E2", "E10"]
    assert Risk.model_validate({"title": "t", "dimension": "nonsense"}).dimension is None
    assert Improvement.model_validate({"title": "t", "dimension_affected": "business"}).dimension_affected == "business_model"
    assert Claim.model_validate({"text": "a", "label": "Verified fact"}).label == "verified_fact"


def test_queries_cover_every_dimension_and_risks():
    queries = build_queries("Tutor finder", {"problem": "Tutors are costly", "key_features": ["search"]}, "idea")
    assert set(queries) == set(DIMENSIONS) | {"risks"}
    assert queries["technical_feasibility"][1][0] == "B"  # technical evidence first


# ------------------------------------------------------------------ evidence


def test_passages_numbered_once_and_grouped():
    evidence = _evidence()
    ids = [i.id for i in evidence.items]
    assert ids == [f"E{n}" for n in range(1, len(ids) + 1)]
    assert len(ids) == len({i.chunk_id for i in evidence.items})  # shared passage numbered once
    assert all("E1" in evidence.groups[d] for d in DIMENSIONS)
    assert "[E1] (source: Source 0" in format_block(evidence.items[:1])
    assert "no evidence retrieved" in format_block([])


def test_validation_removes_unknown_ids_and_relabels_unsupported_facts():
    evidence = _evidence()
    dim = DimensionResult(
        dimension="competition", score=40, confidence="high",
        explanation="Crowded market [E1] and [E99].",
        evidence_ids=["E2", "E42"],
        claims=[
            Claim(text="Rivals charge $20/hour", label="verified_fact", evidence_ids=["E1"]),
            Claim(text="The market grows 40% a year", label="verified_fact", evidence_ids=["E88"]),
            Claim(text="Niche down", label="ai_suggestion"),
        ],
    )
    notes = validate_dimension(dim, evidence)
    assert "[E99]" not in dim.explanation and "[E1]" in dim.explanation
    assert dim.evidence_ids == ["E2", "E1"]
    assert [c.label for c in dim.claims] == ["verified_fact", "assumption", "ai_suggestion"]
    assert "The market grows 40% a year" in dim.assumptions
    assert dim.confidence == "medium"  # 2 sources cited < 3
    assert any("E42" in n and "E88" in n and "E99" in n for n in notes)
    assert any("relabelled" in n for n in notes)


def test_no_evidence_forces_low_confidence():
    evidence = _evidence()
    dim = DimensionResult(dimension="market_opportunity", score=80, confidence="high", explanation="Big.")
    validate_dimension(dim, evidence)
    assert dim.confidence == "low"


def test_three_independent_sources_keep_high_confidence():
    evidence = _evidence()
    dim = DimensionResult(dimension="market_opportunity", score=80, confidence="high",
                          explanation="Big [E1][E2][E3].")
    validate_dimension(dim, evidence)
    assert dim.confidence == "high" and dim.evidence_ids == ["E1", "E2", "E3"]


def test_evidence_link_label_uses_strongest_claim():
    dim = DimensionResult(dimension="competition", score=40, explanation="x", evidence_ids=["E1", "E2", "E3"],
                          claims=[Claim(text="a", label="ai_suggestion", evidence_ids=["E2"]),
                                  Claim(text="b", label="verified_fact", evidence_ids=["E1"])])
    assert evidence_label(dim, "E1") == "verified_fact"
    assert evidence_label(dim, "E2") == "ai_suggestion"
    assert evidence_label(dim, "E3") == "verified_fact"  # cited by the explanation itself


def test_competitor_website_kept_only_when_in_evidence():
    from app.schemas.evaluation import CompetitorItem

    evidence = number_passages({"competition": [_passage(1, content="TutorHub (tutorhub.example) charges $20.")]})
    assert verify_website(CompetitorItem(name="TutorHub", website="tutorhub.example", evidence_ids=["E1"]), evidence)
    assert verify_website(CompetitorItem(name="X", website="made-up.example", evidence_ids=["E1"]), evidence) is None


# ------------------------------------------------------------------ agent calls


def test_evaluate_runs_all_calls_and_repairs_missing_dimension():
    provider = FakeEvalProvider(skip_first="competition")
    draft = evaluator.evaluate(provider, title="Tutor finder", structured={"problem": "p"},
                               idea_text="An app for tutors", evidence=_evidence())
    assert [d.dimension for d in draft.dimensions] == list(DIMENSIONS)
    assert provider.calls.count("DimensionBatch") == 3  # 2 batches + 1 follow-up
    assert {"CritiqueResult", "CompetitorList", "BusinessModelResult"} <= set(provider.calls)
    # unknown dimension on an improvement is pointed at the weakest dimension
    assert draft.critique.improvements[1].dimension_affected == "competition"
    assert draft.usage.calls == len(provider.calls)


def test_fallback_reason_states_direction_and_size():
    dim = DimensionResult(dimension="business_model", score=62, confidence="medium",
                          explanation="Commission revenue is now defined. More text.")
    reason = evaluator.fallback_change_reason({"score": 50, "confidence": "low"}, dim)
    assert "rose by 12 points" in reason and "Commission revenue is now defined" in reason
    assert "low to medium" in reason


# ------------------------------------------------------------------ comparison


def _eval_rows(scores: dict, risks: list[str], baseline: Evaluation | None = None, reason=None):
    e = Evaluation(id=uuid.uuid4(), version_id=uuid.uuid4(),
                   overall_score=round(sum(scores.values()) / 6),
                   risks=[{"title": r} for r in risks],
                   baseline_evaluation_id=baseline.id if baseline else None)
    for d, s in scores.items():
        e.dimensions.append(EvaluationDimension(dimension=d, score=s, confidence="medium",
                                                explanation=f"{d} explanation.", change_reason=reason))
    return e


def test_compare_reports_deltas_with_reasons_and_diffs():
    v1 = ProjectVersion(version_no=1, idea_text="An app for tutors. Students book sessions.")
    v2 = ProjectVersion(version_no=2, idea_text="An app for tutors. Tutors pay a commission.",
                        change_summary="Added commission")
    e1 = _eval_rows(SCORES, ["Low willingness to pay", "Tutor supply"])
    later = {**SCORES, "business_model": SCORES["business_model"] + 12}
    e2 = _eval_rows(later, ["Tutor supply", "Payment disputes"], baseline=e1, reason="Revenue model added.")
    reqs1 = [ProjectRequirement(description="Students can book a session")]
    reqs2 = [ProjectRequirement(description="Students can book a session"),
             ProjectRequirement(description="Tutors are charged a commission")]

    result = compare(e1, e2, v1, v2, reqs1, reqs2)
    row = next(r for r in result["dimensions"] if r["dimension"] == "business_model")
    assert row["delta"] == 12 and row["reason"] == "Revenue model added."
    assert all(r["reason"] for r in result["dimensions"])
    assert result["risks_added"] == ["Payment disputes"]
    assert result["risks_removed"] == ["Low willingness to pay"]
    assert result["requirements_added"] == ["Tutors are charged a commission"]
    assert "Biggest gain: Business model (+12)" in result["summary"]
    ops = [p["op"] for p in result["idea_diff"]]
    assert ops == ["equal", "removed", "added"]


def test_compare_unlinked_evaluations_still_state_a_reason():
    v1, v2 = ProjectVersion(version_no=1, idea_text="a"), ProjectVersion(version_no=3, idea_text="b")
    e1, e2 = _eval_rows(SCORES, []), _eval_rows({**SCORES, "competition": 30}, [])
    row = next(r for r in compare(e1, e2, v1, v2, [], [])["dimensions"] if r["dimension"] == "competition")
    assert row["delta"] == -15 and "fell by 15 points" in row["reason"]


def test_list_and_text_diff_helpers():
    added, removed = diff_lists(["Payment risk for students"], ["Payment risk for the students", "New risk"])
    assert added == ["New risk"] and removed == []
    from app.services.evaluation.compare import _same_risk

    assert _same_risk(
        "Strong competition from existing platforms: Tutoring apps exist",
        "Strong competition from established tutoring platforms: Chegg and others",
    )
    assert not _same_risk("Payment processing challenges: x", "Tutor supply shortage: y")
    assert text_diff("Same. Old.", "Same. New.") == [
        {"op": "equal", "text": "Same."}, {"op": "removed", "text": "Old."}, {"op": "added", "text": "New."}
    ]


# ------------------------------------------------------------------ provider


def test_retry_after_parsing():
    def resp(headers):
        return httpx.Response(429, headers=headers)

    assert _retry_after(resp({"retry-after": "7"})) == 7.0
    assert abs(_retry_after(resp({"x-ratelimit-reset-tokens": "1m2.5s"})) - 62.5) < 1e-6
    assert abs(_retry_after(resp({"x-ratelimit-reset-tokens": "697ms"})) - 0.697) < 1e-6
    assert _retry_after(resp({"retry-after": "9999"})) == 65.0
    assert _retry_after(resp({})) is None
