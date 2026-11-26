"""Version comparison: per-dimension score change with a stated reason, risks, requirements, text."""

from __future__ import annotations

import difflib
import re

from app.models.evaluation import DIMENSIONS, Evaluation
from app.models.project import ProjectRequirement, ProjectVersion
from app.schemas.evaluation import DIMENSION_LABELS
from app.services.evaluation.evaluator import fallback_change_reason

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


_STOP = {"the", "and", "for", "from", "with", "that", "this", "into", "may", "can", "are", "not", "its", "our"}


def _words(text: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2 and w not in _STOP
    }


def _same(a: str, b: str, threshold: float = 0.6) -> bool:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return a.strip().lower() == b.strip().lower()
    return len(wa & wb) / len(wa | wb) >= threshold


def _same_risk(a: str, b: str) -> bool:
    """Risks are reworded between runs: match on the title, or on the whole text."""
    return _same(a.split(":", 1)[0], b.split(":", 1)[0], 0.4) or _same(a, b, 0.5)


def diff_lists(before: list[str], after: list[str], same=_same) -> tuple[list[str], list[str]]:
    """Items only in ``after`` (added) and only in ``before`` (removed), fuzzy-matched."""
    added = [b for b in after if not any(same(a, b) for a in before)]
    removed = [a for a in before if not any(same(a, b) for b in after)]
    return added, removed


def text_diff(before: str, after: str) -> list[dict]:
    """Sentence-level diff of two idea texts."""
    a = [s for s in _SENTENCE.split((before or "").strip()) if s]
    b = [s for s in _SENTENCE.split((after or "").strip()) if s]
    parts: list[dict] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            parts.append({"op": "equal", "text": " ".join(a[i1:i2])})
            continue
        if i2 > i1:
            parts.append({"op": "removed", "text": " ".join(a[i1:i2])})
        if j2 > j1:
            parts.append({"op": "added", "text": " ".join(b[j1:j2])})
    return parts


def _risk_titles(evaluation: Evaluation) -> list[str]:
    return [
        f"{r.get('title', '')}: {r.get('description', '')}".strip(": ")
        for r in (evaluation.risks or [])
        if isinstance(r, dict)
    ]


def compare(
    eval_a: Evaluation,
    eval_b: Evaluation,
    version_a: ProjectVersion,
    version_b: ProjectVersion,
    reqs_a: list[ProjectRequirement],
    reqs_b: list[ProjectRequirement],
) -> dict:
    dims_a = {d.dimension: d for d in eval_a.dimensions}
    dims_b = {d.dimension: d for d in eval_b.dimensions}
    linked = eval_b.baseline_evaluation_id == eval_a.id
    reverse = eval_a.baseline_evaluation_id == eval_b.id

    rows = []
    for key in DIMENSIONS:
        a, b = dims_a.get(key), dims_b.get(key)
        delta = (b.score - a.score) if a and b else None
        if a and b and linked and b.change_reason:
            reason = b.change_reason
        elif a and b and reverse and a.change_reason:
            reason = f"Seen from v{version_a.version_no} (newer): {a.change_reason}"
        elif a and b:
            reason = fallback_change_reason({"score": a.score, "confidence": a.confidence}, b)
        else:
            reason = "Not scored in one of the two evaluations."
        rows.append(
            {
                "dimension": key,
                "label": DIMENSION_LABELS[key],
                "score_a": a.score if a else None,
                "score_b": b.score if b else None,
                "delta": delta,
                "confidence_a": a.confidence if a else None,
                "confidence_b": b.confidence if b else None,
                "reason": reason,
            }
        )

    risks_added, risks_removed = diff_lists(_risk_titles(eval_a), _risk_titles(eval_b), _same_risk)
    reqs_added, reqs_removed = diff_lists(
        [r.description for r in reqs_a], [r.description for r in reqs_b]
    )

    overall_a, overall_b = eval_a.overall_score, eval_b.overall_score
    overall_delta = (overall_b - overall_a) if overall_a is not None and overall_b is not None else None
    moved = [r for r in rows if r["delta"]]
    summary = f"v{version_b.version_no} scores {overall_b} overall against {overall_a} for v{version_a.version_no}"
    summary += f" ({overall_delta:+d})." if overall_delta is not None else "."
    if moved:
        best = max(moved, key=lambda r: r["delta"])
        worst = min(moved, key=lambda r: r["delta"])
        if best["delta"] > 0:
            summary += f" Biggest gain: {best['label']} ({best['delta']:+d})."
        if worst["delta"] < 0:
            summary += f" Biggest drop: {worst['label']} ({worst['delta']:+d})."
    else:
        summary += " No dimension score changed."

    return {
        "a": version_a.version_no,
        "b": version_b.version_no,
        "evaluation_a": eval_a.id,
        "evaluation_b": eval_b.id,
        "overall_a": overall_a,
        "overall_b": overall_b,
        "overall_delta": overall_delta,
        "summary": summary,
        "dimensions": rows,
        "risks_added": risks_added,
        "risks_removed": risks_removed,
        "requirements_added": reqs_added,
        "requirements_removed": reqs_removed,
        "idea_diff": text_diff(version_a.idea_text, version_b.idea_text),
        "change_summary": version_b.change_summary,
    }
