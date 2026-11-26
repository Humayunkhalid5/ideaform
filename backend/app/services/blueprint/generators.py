"""One generator per blueprint section (no database code).

``generate_section`` builds the prompt for one artifact from the idea, the stored outputs
of the sections it depends on, the latest evaluation and KB-B references, calls the model
for structured JSON, checks it, and renders Markdown with diagrams. Regenerating a section
reuses the stored inputs, so nothing else is redone (AI_DESIGN 7).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.schemas.blueprint import (
    RESULT_SCHEMAS,
    ApiResult,
    ArchitectureResult,
    PrdResult,
    ProductDesignResult,
    RoadmapResult,
    SchemaResult,
)
from app.services.blueprint import prompts, render
from app.services.llm import ChatMessage, generate_json
from app.services.llm.base import LLMProvider, LLMResult, LLMTier

# what each section is built from (and so what makes it stale when it changes)
DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "ui_ux": (),
    "architecture": ("ui_ux",),
    "database_schema": ("ui_ux", "architecture"),
    "api_spec": ("ui_ux", "architecture", "database_schema"),
    "prd": ("ui_ux", "architecture"),
    "roadmap": ("ui_ux", "architecture", "database_schema", "api_spec", "prd"),
}
ORDER = ("ui_ux", "architecture", "database_schema", "api_spec", "prd", "roadmap")
USES_REFERENCES = {"architecture", "database_schema", "api_spec"}
USES_EVALUATION = {"ui_ux", "prd"}

# strong model for the two agents and the schema, fast model for the documents: the two
# tiers have separate per-minute budgets, so this also spreads the load.
TIERS = {
    "ui_ux": LLMTier.STRONG,
    "architecture": LLMTier.STRONG,
    "database_schema": LLMTier.STRONG,
    "api_spec": LLMTier.FAST,
    "prd": LLMTier.FAST,
    "roadmap": LLMTier.FAST,
}
MAX_TOKENS = {"ui_ux": 3000, "architecture": 3000, "database_schema": 3000,
              "api_spec": 3400, "prd": 2600, "roadmap": 2600}
TEMPERATURE = 0.3
REASONING = "low"
EDITED_CHARS = 2_400  # how much of a user-edited upstream section the prompt sees


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = 0
    model: str | None = None

    def add(self, result: LLMResult) -> None:
        self.tokens_in += result.tokens_in
        self.tokens_out += result.tokens_out
        self.calls += 1
        self.model = self.model or result.model


@dataclass
class Upstream:
    """A stored section used as input: its structured data, or the user's edited text."""

    artifact_type: str
    version: int
    data: dict | None
    content: str
    edited: bool


@dataclass
class Context:
    title: str
    idea: str  # the IDEA block
    evaluation: str | None = None  # the EVALUATION block, when the version was evaluated
    references: list[dict] = field(default_factory=list)  # id, title, url, content
    requirements: list[dict] = field(default_factory=list)  # kind, priority, text (stored rows)


@dataclass
class Section:
    artifact_type: str
    data: dict
    markdown: str
    notes: list[str]
    based_on: dict[str, int]


# ------------------------------------------------------------------ input blocks


def idea_block(title: str, category: str | None, idea_text: str, structured: dict | None,
               requirements: list[dict]) -> str:
    s = structured or {}
    lines = [f"Title: {title}", f"Category: {category or s.get('category') or 'unknown'}"]
    if s.get("problem"):
        lines.append(f"Problem: {s['problem']}")
    for key, label in (("target_users", "Target users"), ("key_features", "Key features"),
                       ("technologies_mentioned", "Technologies mentioned"),
                       ("missing_information", "Missing information")):
        if s.get(key):
            lines.append(f"{label}: " + "; ".join(map(str, s[key])))
    lines.append(f"Description: {idea_text.strip()[:2_000]}")
    if requirements:
        lines.append("Requirements:")
        for r in requirements[:30]:
            flag = " [confirmed]" if r.get("confirmed") else ""
            lines.append(f"- ({r.get('req_type')}, {r.get('priority') or 'should'}){flag} {r.get('description')}")
    return "\n".join(lines)


def evaluation_block(overall: int | None, dimensions: list[tuple[str, int, str]],
                     risks: list[dict], business: dict | None) -> str:
    lines = [f"Overall score: {overall}/100 (an estimate)"] if overall is not None else []
    lines += [f"- {name}: {score} ({confidence})" for name, score, confidence in dimensions]
    if risks:
        lines.append("Top risks:")
        lines += [f"- {r.get('title')}: {r.get('mitigation') or r.get('description') or ''}" for r in risks[:5]]
    if business:
        streams = business.get("revenue_streams") or []
        if streams:
            lines.append("Revenue streams: " + "; ".join(map(str, streams)))
    return "\n".join(lines)


def references_block(refs: list[dict], max_chars: int = 420) -> str:
    if not refs:
        return "(no technical references were retrieved; rely on well-known practice and cite nothing)"
    out = []
    for r in refs:
        body = r["content"] if len(r["content"]) <= max_chars else r["content"][:max_chars] + "…"
        out.append(f"[{r['id']}] ({r.get('title') or 'untitled'}) {body}")
    return "\n".join(out)


def _summary(up: Upstream) -> str:
    """Compact text of a stored section for the prompts of the sections built on it."""
    if up.edited or not up.data:
        text = up.content.strip()
        return text if len(text) <= EDITED_CHARS else text[:EDITED_CHARS] + "\n…"
    d = up.data.get("result") or {}
    t = up.artifact_type
    if t == "ui_ux":
        reqs = [f"- ({r.get('kind')}, {r.get('priority')}) {r.get('text')}" for r in d.get("requirements", [])]
        flows = [f"- {f.get('name')}: " + " > ".join(f.get("steps", [])[:8]) for f in d.get("user_flows", [])]
        screens = [f"- {s.get('name')} ({s.get('route') or '-'}): {s.get('purpose', '')}" for s in d.get("screens", [])]
        return "\n".join(["Requirements:", *reqs, "User flows:", *flows, "Screens:", *screens])
    if t == "architecture":
        stack = [f"- {s.get('layer')}: {s.get('choice')}" for s in d.get("stack", [])]
        comps = [f"- {c.get('id')} ({c.get('kind')}): {c.get('responsibility', '')}" for c in d.get("components", [])]
        sec = [f"- {s}" for s in d.get("security", [])[:5]]
        return "\n".join(["Stack:", *stack, "Components:", *comps, "Security:", *sec])
    if t == "database_schema":
        return "Tables:\n" + "\n".join(
            f"- {e.get('name')}(" + ", ".join(
                f.get("name", "") + (" PK" if f.get("pk") else "") + (f" FK->{f.get('fk')}" if f.get("fk") else "")
                for f in e.get("fields", [])
            ) + ")"
            for e in d.get("entities", [])
        )
    if t == "api_spec":
        return "Endpoints:\n" + "\n".join(
            f"- {e.get('method')} {e.get('path')}: {e.get('summary', '')}" for e in d.get("endpoints", [])
        )
    if t == "prd":
        feats = [f"- ({f.get('priority')}) {f.get('name')}: {f.get('description', '')}" for f in d.get("features", [])]
        return "\n".join(["Goals:", *[f"- {g}" for g in d.get("goals", [])], "Features:", *feats])
    return json.dumps(d)[:EDITED_CHARS]


# ------------------------------------------------------------------ checks


def strip_unknown_refs(value, valid: set[str]):
    """Remove [R#] markers and reference ids that are not in the reference catalogue."""
    if isinstance(value, str):
        return re.sub(r"\s?\[(R\d{1,2})\]", lambda m: m.group(0) if m.group(1).upper() in valid else "", value,
                      flags=re.IGNORECASE)
    if isinstance(value, list):
        if all(isinstance(v, str) and re.fullmatch(r"R\d{1,2}", v) for v in value) and value:
            return [v for v in value if v in valid]
        return [strip_unknown_refs(v, valid) for v in value]
    if isinstance(value, dict):
        return {k: strip_unknown_refs(v, valid) for k, v in value.items()}
    return value


def _render(artifact_type: str, result: BaseModel, refs: list[dict]) -> tuple[str, list[str]]:
    if artifact_type == "ui_ux":
        return render.render_ui_ux(result), []
    if artifact_type == "architecture":
        notes = render.review_architecture(result)
        return render.render_architecture(result, refs, notes), notes
    if artifact_type == "database_schema":
        notes = render.review_schema(result)
        return render.render_schema(result, refs, notes), notes
    if artifact_type == "api_spec":
        notes = render.review_api(result)
        return render.render_api(result, refs, notes), notes
    if artifact_type == "roadmap":
        return render.render_roadmap(result), []
    raise ValueError(artifact_type)


# ------------------------------------------------------------------ the call


def generate_section(
    provider: LLMProvider,
    artifact_type: str,
    ctx: Context,
    upstream: dict[str, Upstream],
    usage: Usage,
    instructions: str | None = None,
) -> Section:
    schema = RESULT_SCHEMAS[artifact_type]
    parts = [f"IDEA:\n{ctx.idea}"]
    if artifact_type in USES_EVALUATION and ctx.evaluation:
        parts.append(f"EVALUATION (estimates):\n{ctx.evaluation}")
    for dep in DEPENDENCIES[artifact_type]:
        up = upstream.get(dep)
        if up is not None:
            label = dep.replace("_", " ").upper() + (" (edited by the user)" if up.edited else "")
            parts.append(f"{label}:\n{_summary(up)}")
    if artifact_type in USES_REFERENCES:
        parts.append(f"REFERENCES:\n{references_block(ctx.references)}")
    if instructions and instructions.strip():
        parts.append(prompts.INSTRUCTIONS_NOTE.format(instructions=instructions.strip()[:2_000]))

    messages = [
        ChatMessage.system(prompts.COMMON_RULES + "\n\n" + prompts.TASKS[artifact_type]),
        ChatMessage.user("\n\n".join(parts)),
    ]
    result, call = generate_json(
        provider,
        messages,
        schema,
        tier=TIERS[artifact_type],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS[artifact_type],
        reasoning_effort=REASONING,
    )
    usage.add(call)

    valid = {r["id"] for r in ctx.references}
    result = schema.model_validate(strip_unknown_refs(result.model_dump(), valid))

    if artifact_type == "prd":
        design = upstream.get("ui_ux")
        reqs = ((design.data or {}).get("result") or {}).get("requirements", []) if design and not design.edited else []
        markdown, notes = render.render_prd(result, reqs or ctx.requirements), []
    else:
        markdown, notes = _render(artifact_type, result, ctx.references)

    used = render._used_refs(markdown)
    return Section(
        artifact_type=artifact_type,
        data={
            "result": result.model_dump(),
            "review_notes": notes,
            "references": [{k: r[k] for k in ("id", "title", "url")} for r in ctx.references if r["id"] in used],
        },
        markdown=markdown,
        notes=notes,
        based_on={dep: upstream[dep].version for dep in DEPENDENCIES[artifact_type] if dep in upstream},
    )


__all__ = [
    "ApiResult", "ArchitectureResult", "Context", "DEPENDENCIES", "ORDER", "PrdResult",
    "ProductDesignResult", "RoadmapResult", "SchemaResult", "Section", "Upstream", "Usage",
    "evaluation_block", "generate_section", "idea_block",
]
