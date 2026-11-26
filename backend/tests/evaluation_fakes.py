"""A fake LLM provider for Phase 3 tests: answers by the schema the caller asked for."""

from __future__ import annotations

import json

from app.models.evaluation import DIMENSIONS
from app.services.llm.base import LLMProvider, LLMResult

SCORES = {
    "technical_feasibility": 72,
    "market_opportunity": 64,
    "competition": 45,
    "business_model": 50,
    "resource_requirements": 66,
    "execution_complexity": 58,
}


class FakeEvalProvider(LLMProvider):
    """Returns canned JSON per schema. ``bump`` raises scores on a re-evaluation."""

    name = "fake"
    fast_model = "fake-fast"
    strong_model = "fake-strong"

    def __init__(self, *, bump: int = 0, skip_first: str | None = None, with_reason: bool = True):
        self.bump = bump
        self.skip_first = skip_first  # leave this dimension out of the first answer
        self.with_reason = with_reason
        self.calls: list[str] = []

    def health(self):
        return True, "ok"

    def complete(self, messages, *, tier=None, temperature=None, max_tokens=None,
                 json_mode=False, reasoning_effort=None) -> LLMResult:
        schema = messages[-1].content
        name = next(
            (n for n in ("DimensionBatch", "CritiqueResult", "CompetitorList",
                         "BusinessModelResult", "RewrittenIdea") if f'"title":"{n}"' in schema),
            "unknown",
        )
        self.calls.append(name)
        body = getattr(self, f"_{name}", lambda m: {})(messages)
        return LLMResult(text=json.dumps(body), model=self.strong_model, tokens_in=40, tokens_out=60)

    def _DimensionBatch(self, messages):
        task = messages[0].content
        wanted = [d for d in DIMENSIONS if f"- {d}:" in task]
        if self.skip_first in wanted and self.calls.count("DimensionBatch") == 1:
            wanted.remove(self.skip_first)
        with_baseline = "PREVIOUS EVALUATION" in messages[1].content
        dims = []
        for d in wanted:
            dims.append({
                "dimension": d.replace("_", " ").title(),  # the model drifts on casing
                "score": min(100, SCORES[d] + (self.bump if with_baseline else 0)),
                "confidence": "High",
                "explanation": f"{d} looks reasonable [E1], see also [E99].",
                "evidence_ids": ["E1", "E2", "E77"],
                "claims": [
                    {"text": f"{d} is supported by a source", "label": "verified_fact", "evidence_ids": ["E1"]},
                    {"text": f"{d} market grows 40% a year", "label": "verified_fact", "evidence_ids": []},
                    {"text": f"Start with one city for {d}", "label": "ai_suggestion"},
                ],
                "assumptions": ["Users will pay"],
                "recommendations": ["Interview ten users"],
                "change_reason": (
                    f"The idea now addresses {d}." if with_baseline and self.with_reason else None
                ),
            })
        return {"summary": "A plausible idea with gaps.", "dimensions": dims}

    def _CritiqueResult(self, messages):
        return {
            "risks": [
                {"title": "Low willingness to pay", "description": "Students are price sensitive",
                 "severity": "high", "likelihood": "medium", "mitigation": "Freemium tier",
                 "dimension": "business_model", "evidence_ids": ["E1", "E50"]},
                {"title": "Tutor supply", "description": "Hard to recruit vetted tutors",
                 "severity": "medium", "likelihood": "medium", "mitigation": "Partner with universities",
                 "dimension": "execution_complexity", "evidence_ids": []},
            ],
            "devils_advocate": "Free alternatives already exist and students rarely pay.",
            "hidden_assumptions": ["Tutors want another platform"],
            "must_be_true": ["Students pay at least a small fee"],
            "improvements": [
                {"title": "Add a commission model", "rationale": "Clarifies revenue",
                 "change": "Charge tutors a 10% commission per booked session.",
                 "expected_effect": "Business model score rises", "dimension_affected": "business model",
                 "evidence_ids": ["E1"]},
                {"title": "Focus on exam prep", "rationale": "Sharper niche",
                 "change": "Start with exam preparation for first-year engineering students.",
                 "expected_effect": "Competition score rises", "dimension_affected": "unknown-dim"},
            ],
            "alternatives": ["Peer study groups", "B2B with universities"],
        }

    def _CompetitorList(self, messages):
        return {"competitors": [
            {"name": "TutorHub", "website": "tutorhub.example", "pricing": "$20/hour",
             "strengths": ["Large catalogue"], "weaknesses": ["Expensive"], "evidence_ids": ["E1"]},
            {"name": "Invented Corp", "website": "invented.example", "evidence_ids": []},
        ]}

    def _BusinessModelResult(self, messages):
        return {"customer_segments": ["University students"], "value_proposition": "Affordable vetted tutors",
                "revenue_streams": ["Commission"], "pricing_options": [{"name": "Commission", "model": "10%"}],
                "evidence_ids": ["E2", "E40"]}

    def _RewrittenIdea(self, messages):
        return {"idea_text": "An app that helps university students book affordable vetted tutors. "
                             "Tutors pay a 10% commission per booked session.",
                "change_summary": "Added a commission model."}
