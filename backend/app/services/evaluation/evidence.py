"""Evidence for the Evaluation Agent: gather, number, and validate (AI_DESIGN 4.3, 6.7).

* ``gather_evidence`` runs hybrid retrieval once per dimension (plus risks) over
  KB-A/B and the project's KB-C, de-duplicates the passages and numbers them
  E1..En. The same numbering is stored with the evaluation, so a citation in the
  UI opens exactly the passage the model saw.
* ``validate_dimension`` and friends enforce the rules after generation: every
  cited id must exist, a ``verified_fact`` needs at least one valid citation
  (otherwise it is relabelled ``assumption``), and confidence cannot exceed what
  the number of independent sources allows (AI_DESIGN 5.3).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from app.schemas.evaluation import DIMENSION_LABELS, Claim, DimensionResult, normalise_ids
from app.services.knowledge.retrieval import Filters, Passage, Scope, search

PER_QUERY = 4
MAX_EVIDENCE = 26
SNIPPET_CHARS = 450

# query template and knowledge bases per dimension (KB-A business, KB-B technical, KB-C project)
DIMENSION_QUERIES: dict[str, tuple[str, list[str]]] = {
    "technical_feasibility": ("{features} {tech} implementation architecture technology", ["B", "C", "A"]),
    "market_opportunity": ("{problem} {users} market size demand growth trends", ["A", "C"]),
    "competition": ("{title} competitors alternatives similar products {features}", ["C", "A"]),
    "business_model": ("{title} pricing revenue model subscription commission {users}", ["A", "C"]),
    "resource_requirements": ("{features} {tech} cost team infrastructure budget hiring", ["A", "B", "C"]),
    "execution_complexity": ("{problem} regulation compliance integration operations scale", ["A", "B", "C"]),
}
EXTRA_QUERIES: dict[str, tuple[str, list[str]]] = {
    "risks": ("{domain} startup failure reasons risks {problem}", ["A", "C"]),
}

_REF = re.compile(r"\[(E\d{1,3})\]", re.IGNORECASE)


@dataclass
class EvidenceItem:
    id: str
    chunk_id: str
    source_id: str
    kb: str
    title: str | None
    url: str | None
    publisher: str | None
    published_at: str | None
    content: str

    def as_ref(self) -> dict:
        data = asdict(self)
        data["snippet"] = data.pop("content")[:SNIPPET_CHARS]
        return data


@dataclass
class EvidenceSet:
    items: list[EvidenceItem] = field(default_factory=list)
    groups: dict[str, list[str]] = field(default_factory=dict)  # dimension/risks -> ["E1", ...]

    @property
    def by_id(self) -> dict[str, EvidenceItem]:
        return {item.id: item for item in self.items}

    def subset(self, keys: list[str]) -> list[EvidenceItem]:
        wanted: list[str] = []
        for key in keys:
            for ref in self.groups.get(key, []):
                if ref not in wanted:
                    wanted.append(ref)
        index = self.by_id
        return [index[r] for r in sorted(wanted, key=lambda r: int(r[1:]))]

    def catalogue(self) -> list[dict]:
        return [item.as_ref() for item in self.items]


def _join(values, limit: int = 3) -> str:
    return " ".join(str(v) for v in (values or [])[:limit])


def query_terms(title: str, structured: dict | None, idea_text: str) -> dict[str, str]:
    s = structured or {}
    classification = s.get("classification") or {}
    return {
        "title": title,
        "problem": (s.get("problem") or idea_text[:160]).strip(),
        "users": _join(s.get("target_users"), 2),
        "features": _join(s.get("key_features"), 3),
        "tech": _join(s.get("technologies_mentioned"), 3),
        "domain": s.get("sub_domain") or classification.get("category") or s.get("category") or "",
    }


def build_queries(title: str, structured: dict | None, idea_text: str) -> dict[str, tuple[str, list[str]]]:
    terms = query_terms(title, structured, idea_text)
    out = {}
    for key, (template, kbs) in {**DIMENSION_QUERIES, **EXTRA_QUERIES}.items():
        query = " ".join(template.format(**terms).split())[:300]
        out[key] = (query, kbs)
    return out


def number_passages(results: dict[str, list[Passage]], limit: int = MAX_EVIDENCE) -> EvidenceSet:
    """Number unique passages E1..En in query order and remember which query found each."""
    evidence = EvidenceSet()
    seen: dict[uuid.UUID, str] = {}
    # round-robin so every dimension gets evidence before the cap is reached
    depth = max((len(v) for v in results.values()), default=0)
    for rank in range(depth):
        for key, passages in results.items():
            if rank >= len(passages):
                continue
            p = passages[rank]
            ref = seen.get(p.chunk_id)
            if ref is None:
                if len(evidence.items) >= limit:
                    continue
                ref = f"E{len(evidence.items) + 1}"
                seen[p.chunk_id] = ref
                when = p.published_at or (p.retrieved_at.date() if p.retrieved_at else None)
                evidence.items.append(
                    EvidenceItem(
                        id=ref,
                        chunk_id=str(p.chunk_id),
                        source_id=str(p.source_id),
                        kb=p.kb,
                        title=p.title,
                        url=p.url,
                        publisher=p.publisher,
                        published_at=when.isoformat() if when else None,
                        content=" ".join(p.content.split()),
                    )
                )
            group = evidence.groups.setdefault(key, [])
            if ref not in group:
                group.append(ref)
    for key in results:
        evidence.groups.setdefault(key, [])
    return evidence


def gather_evidence(
    db: Session,
    *,
    title: str,
    structured: dict | None,
    idea_text: str,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    per_query: int = PER_QUERY,
) -> EvidenceSet:
    scope = Scope(user_id=user_id, project_id=project_id)
    results: dict[str, list[Passage]] = {}
    for key, (query, kbs) in build_queries(title, structured, idea_text).items():
        results[key] = search(db, query, scope=scope, filters=Filters(kbs=kbs), k=per_query)
    return number_passages(results)


def format_block(items: list[EvidenceItem], max_chars: int = SNIPPET_CHARS) -> str:
    """The numbered evidence block of AI_DESIGN 4.3, using the global E-ids."""
    if not items:
        return "(no evidence retrieved: every factual statement must be an assumption)"
    lines = []
    for item in items:
        body = item.content if len(item.content) <= max_chars else item.content[:max_chars] + "…"
        lines.append(
            f"[{item.id}] (source: {item.title or 'untitled'}, {item.published_at or 'n.d.'}, "
            f"{item.url or 'uploaded document'}) {body}"
        )
    return "\n".join(lines)


# ------------------------------------------------------------------ validation


def filter_ids(ids, valid: set[str]) -> tuple[list[str], list[str]]:
    kept, dropped = [], []
    for ref in normalise_ids(ids):
        (kept if ref in valid else dropped).append(ref)
    return kept, dropped


def _strip_invalid_refs(text: str, valid: set[str]) -> tuple[str, list[str], list[str]]:
    found, dropped = [], []

    def repl(match: re.Match) -> str:
        ref = match.group(1).upper()
        if ref in valid:
            if ref not in found:
                found.append(ref)
            return f"[{ref}]"
        dropped.append(ref)
        return ""

    cleaned = _REF.sub(repl, text or "")
    return re.sub(r"\s+([.,;:])", r"\1", re.sub(r"[ \t]{2,}", " ", cleaned)).strip(), found, dropped


def validate_dimension(dim: DimensionResult, evidence: EvidenceSet) -> list[str]:
    """Apply the evidence rules to one dimension in place; return human-readable notes."""
    index = evidence.by_id
    valid = set(index)
    label = DIMENSION_LABELS.get(dim.dimension, dim.dimension)
    notes: list[str] = []
    dropped_all: list[str] = []

    explanation, in_text, dropped = _strip_invalid_refs(dim.explanation, valid)
    dim.explanation = explanation
    dropped_all += dropped

    cited, dropped = filter_ids(dim.evidence_ids, valid)
    dropped_all += dropped

    relabelled = 0
    claims: list[Claim] = []
    for claim in dim.claims:
        text, refs_in_claim, dropped = _strip_invalid_refs(claim.text, valid)
        ids, dropped_ids = filter_ids(claim.evidence_ids + refs_in_claim, valid)
        dropped_all += dropped + dropped_ids
        claim.text, claim.evidence_ids = text, ids
        if not text:
            continue
        if claim.label == "verified_fact" and not ids:
            claim.label = "assumption"
            relabelled += 1
            if text not in dim.assumptions:
                dim.assumptions.append(text)
        claims.append(claim)
    dim.claims = claims

    ordered: list[str] = []
    for ref in cited + in_text + [r for c in claims for r in c.evidence_ids]:
        if ref not in ordered:
            ordered.append(ref)
    dim.evidence_ids = ordered

    if dropped_all:
        unique = sorted(set(dropped_all), key=lambda r: int(r[1:]))
        notes.append(f"{label}: removed citations to evidence that does not exist ({', '.join(unique)}).")
    if relabelled:
        notes.append(
            f"{label}: {relabelled} unsupported factual claim(s) relabelled as assumptions."
        )

    sources = {index[r].source_id for r in ordered}
    if not sources:
        if dim.confidence != "low":
            notes.append(f"{label}: no supporting evidence, confidence set to low.")
        dim.confidence = "low"
    elif len(sources) < 3 and dim.confidence == "high":
        dim.confidence = "medium"
        notes.append(f"{label}: fewer than 3 independent sources, confidence capped at medium.")
    return notes


def validate_ids_on(items: list, evidence: EvidenceSet, attr: str = "evidence_ids") -> int:
    """Drop unknown ids from ``items[*].evidence_ids``; return how many were removed."""
    valid = set(evidence.by_id)
    removed = 0
    for item in items:
        kept, dropped = filter_ids(getattr(item, attr), valid)
        setattr(item, attr, kept)
        removed += len(dropped)
    return removed
