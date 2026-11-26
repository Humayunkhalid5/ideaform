"""Idea clarity (SRS UC-1 alternate flow: "idea too vague, so the system asks clarifying
questions") and requirement priority calibration. Deterministic: no extra model call."""

from __future__ import annotations

import re

MIN_WORDS = 15
CORE_FIELDS = ("problem", "target_users", "key_features")

_TEMPLATES = (
    (r"problem|pain|need", "What problem does it solve, and who has that problem today?"),
    (r"user|customer|audience|student|segment", "Who exactly will use it? Describe the main type of user."),
    (r"feature|function|capabilit|what it does", "What are the three most important things it lets users do?"),
    (r"platform|technolog|app|web|mobile|channel|interface", "Where will people use it (web, mobile app, WhatsApp, in person)?"),
    (r"pric|revenue|monet|business model|payment|cost", "How will it make money, and roughly what will users pay?"),
    (r"region|area|location|market|city|country", "Where will it launch first?"),
    (r"compet|alternative", "What do people use instead today?"),
)


def _question(item: str) -> str:
    low = item.lower()
    for pattern, question in _TEMPLATES:
        if re.search(pattern, low):
            return question
    return f"Can you say more about the {item.strip().rstrip('.').lower()}?"


def assess(idea_text: str, structured: dict, confidence: str | None) -> dict:
    """``{"vague": bool, "reasons": [...], "questions": [...]}`` for a structured idea."""
    words = len(idea_text.split())
    empty = [f for f in CORE_FIELDS if not structured.get(f)]
    reasons = []
    if words < MIN_WORDS:
        reasons.append(f"The description has only {words} words.")
    if confidence == "low":
        reasons.append("The category could not be determined with confidence.")
    if len(empty) >= 2:
        reasons.append("It does not say " + " or ".join(f.replace("_", " ") for f in empty) + ".")

    questions: list[str] = []
    for item in structured.get("missing_information") or []:
        q = _question(str(item))
        if q not in questions:
            questions.append(q)
    for field in empty:
        q = _question(field)
        if q not in questions:
            questions.insert(0, q)
    if words < MIN_WORDS:
        questions.append("Describe in a few sentences how it works from the user's point of view.")
    vague = bool(reasons)
    return {"vague": vague, "reasons": reasons, "questions": questions[:5] if vague else questions[:3]}


def calibrate_priority(priority: str, source: str) -> str:
    """Only the user's own words can make something a must: AI suggestions top out at should."""
    if source == "ai_suggestion" and priority == "must":
        return "should"
    return priority
