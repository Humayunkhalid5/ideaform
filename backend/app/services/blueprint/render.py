"""Markdown templates, Mermaid builders and automatic review checks for the blueprint.

The model only fills structured fields; everything a reader sees (headings, tables,
diagrams) is rendered here, so section layout is fixed (AI_DESIGN 6.5) and every Mermaid
diagram is syntactically valid by construction: identifiers and labels are sanitised
instead of trusting model-written diagram code.
"""

from __future__ import annotations

import re

from app.schemas.blueprint import (
    ApiResult,
    ArchitectureResult,
    PrdResult,
    ProductDesignResult,
    RoadmapResult,
    SchemaResult,
)

# ------------------------------------------------------------------ helpers


def _ident(value: str, prefix: str = "n") -> str:
    """A Mermaid-safe identifier: letters, digits, underscore; starts with a letter."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_") or prefix
    return s if s[0].isalpha() else f"{prefix}_{s}"


def _label(value: str, limit: int = 60) -> str:
    """Text for inside a quoted Mermaid label: no quotes, brackets, pipes or newlines."""
    s = re.sub(r"[\"`|<>{}\[\]#;]", "", value or "").replace("\n", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s[: limit - 1] + "…" if len(s) > limit else s


def _cell(value: str) -> str:
    """Text for a Markdown table cell."""
    return (value or "").replace("|", "\\|").replace("\n", " ").strip() or "—"


def _bullets(items: list[str], empty: str = "None stated.") -> str:
    items = [i.strip() for i in items if i and i.strip()]
    return "\n".join(f"- {i}" for i in items) if items else f"_{empty}_"


def _mermaid(code: str) -> str:
    return f"```mermaid\n{code}\n```"


def _refs_footer(references: list[dict], used: set[str]) -> str:
    rows = [r for r in references if r["id"] in used]
    if not rows:
        return ""
    lines = [f"- [{r['id']}] {r.get('title') or 'Untitled'}" + (f" ({r['url']})" if r.get("url") else "") for r in rows]
    return "\n\n## References (KB-B)\n\n" + "\n".join(lines)


def _used_refs(text: str) -> set[str]:
    return {m.upper() for m in re.findall(r"\[(R\d{1,2})\]", text, flags=re.IGNORECASE)}


def _notes_section(notes: list[str]) -> str:
    if not notes:
        return ""
    return "\n\n## Review notes (automatic checks)\n\n" + _bullets(notes)


# ------------------------------------------------------------------ diagrams

_SHAPES = {
    "frontend": ('["', '"]'),
    "backend": ('["', '"]'),
    "service": ('["', '"]'),
    "worker": ('[/"', '"/]'),
    "database": ('[("', '")]'),
    "cache": ('[("', '")]'),
    "storage": ('[("', '")]'),
    "queue": ('[/"', '"/]'),
    "ai": ('{{"', '"}}'),
    "external": ('(["', '"])'),
}


def architecture_diagram(arch: ArchitectureResult) -> str:
    ids: dict[str, str] = {}
    lines = ["flowchart LR"]
    for comp in arch.components:
        node = _ident(comp.id or comp.name)
        while node in ids.values():
            node += "_"
        ids[comp.id] = node
        ids.setdefault(comp.name, node)
        left, right = _SHAPES.get(comp.kind, _SHAPES["service"])
        lines.append(f"    {node}{left}{_label(comp.name, 40)}{right}")
    for conn in arch.connections:
        a, b = ids.get(conn.source), ids.get(conn.target)
        if not a or not b or a == b:
            continue
        label = _label(conn.label, 32)
        lines.append(f"    {a} -->|\"{label}\"| {b}" if label else f"    {a} --> {b}")
    if len(lines) == 1:
        lines.append('    empty["No components described"]')
    return "\n".join(lines)


_CARD = {"one_to_one": "||--||", "one_to_many": "||--o{", "many_to_many": "}o--o{"}


def _entity_name(name: str) -> str:
    return _ident(name, "E").upper()


def _attr_type(value: str) -> str:
    t = re.sub(r"\(.*?\)", "", value or "text").strip().lower()
    return _ident(t.replace(" ", "_"), "t") if t else "text"


def er_diagram(schema: SchemaResult) -> str:
    names = {e.name.lower(): _entity_name(e.name) for e in schema.entities}
    lines = ["erDiagram"]
    for entity in schema.entities:
        lines.append(f"    {_entity_name(entity.name)} {{")
        for f in entity.fields[:24]:
            keys = ",".join(k for k, on in (("PK", f.pk), ("FK", bool(f.fk))) if on)
            lines.append(f"        {_attr_type(f.type)} {_ident(f.name, 'f')}" + (f" {keys}" if keys else ""))
        lines.append("    }")
    for rel in schema.relationships:
        a, b = names.get(rel.source.lower()), names.get(rel.target.lower())
        if a and b:
            lines.append(f'    {a} {_CARD[rel.cardinality]} {b} : "{_label(rel.label, 30) or "has"}"')
    return "\n".join(lines)


def flow_diagram(flow_name: str, steps: list[str]) -> str:
    lines = ["flowchart TD"]
    prev = None
    for i, step in enumerate(steps[:10]):
        node = f"s{i}"
        lines.append(f'    {node}["{_label(step, 48)}"]')
        if prev:
            lines.append(f"    {prev} --> {node}")
        prev = node
    if prev is None:
        lines.append(f'    s0["{_label(flow_name, 48)}"]')
    return "\n".join(lines)


def roadmap_diagram(roadmap: RoadmapResult) -> str:
    lines = ["flowchart LR"]
    prev = None
    for i, phase in enumerate(roadmap.phases[:8]):
        node = f"p{i + 1}"
        label = _label(phase.name, 36) + (f" · {_label(phase.duration, 18)}" if phase.duration else "")
        lines.append(f'    {node}["{label}"]')
        if prev:
            lines.append(f"    {prev} --> {node}")
        prev = node
    if prev is None:
        lines.append('    p1["No phases described"]')
    return "\n".join(lines)


# ------------------------------------------------------------------ automatic review checks


def review_architecture(arch: ArchitectureResult) -> list[str]:
    notes = []
    kinds = {c.kind for c in arch.components}
    if not arch.components:
        notes.append("No components were described.")
    if arch.components and not kinds & {"database", "storage"}:
        notes.append("No database or storage component: say where data is persisted.")
    if not any(re.search(r"auth|login|token|session|oauth|jwt", s, re.I) for s in arch.security):
        notes.append("Security notes do not mention authentication.")
    linked = {c.source for c in arch.connections} | {c.target for c in arch.connections}
    lonely = [c.name for c in arch.components if c.id not in linked and c.name not in linked]
    if arch.connections and lonely:
        notes.append(f"Not connected to anything: {', '.join(lonely[:5])}.")
    backends = [c for c in arch.components if c.kind in ("backend", "service")]
    if len(backends) == 1 and not kinds & {"cache", "queue", "worker"} and not arch.scalability:
        notes.append("A single backend with no cache, queue or scalability notes is a single point of failure.")
    if not arch.stack:
        notes.append("No technology stack was given.")
    return notes


def review_schema(schema: SchemaResult) -> list[str]:
    notes = []
    known = {e.name.lower() for e in schema.entities}
    for e in schema.entities:
        if not any(f.pk for f in e.fields):
            notes.append(f"`{e.name}` has no primary key.")
        for f in e.fields:
            if f.fk and f.fk.split(".")[0].lower() not in known:
                notes.append(f"`{e.name}.{f.name}` references `{f.fk}`, which is not in the schema.")
    for rel in schema.relationships:
        missing = [n for n in (rel.source, rel.target) if n.lower() not in known]
        if missing:
            notes.append(f"Relationship uses unknown entity {', '.join(f'`{m}`' for m in missing)}.")
    if schema.entities and not any(re.search(r"user|account|member", e.name, re.I) for e in schema.entities):
        notes.append("No user or account entity: say who owns the data.")
    return notes


def review_api(api: ApiResult) -> list[str]:
    notes = []
    seen: set[tuple[str, str]] = set()
    for ep in api.endpoints:
        key = (ep.method, ep.path)
        if key in seen:
            notes.append(f"Duplicate endpoint {ep.method} {ep.path}.")
        seen.add(key)
        public_write = ep.method != "GET" and not ep.auth_required
        if public_write and not re.search(r"auth|login|register|signup|sign-up|token|webhook", ep.path, re.I):
            notes.append(f"{ep.method} {ep.path} changes data without authentication.")
    if api.endpoints and not api.authentication:
        notes.append("The authentication scheme is not described.")
    return notes


# ------------------------------------------------------------------ documents


def render_ui_ux(d: ProductDesignResult) -> str:
    parts = ["# UI/UX concepts", d.summary or ""]
    parts.append("## User roles\n\n" + (
        "\n".join(f"- **{r.name}**: {', '.join(r.goals) or 'goals not stated'}" for r in d.user_roles)
        or "_None stated._"
    ))
    parts.append("## User flows")
    for flow in d.user_flows[:6]:
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(flow.steps, 1)) or "_No steps._"
        parts.append(f"### {flow.name}\n\n_Actor: {flow.actor}_\n\n{steps}\n\n{_mermaid(flow_diagram(flow.name, flow.steps))}")
    if not d.user_flows:
        parts.append("_No flows described._")
    rows = "\n".join(
        f"| {_cell(s.name)} | {_cell(s.route or '')} | {_cell(s.purpose)} | {_cell(', '.join(s.key_elements))} |"
        for s in d.screens
    )
    parts.append("## Screens\n\n| Screen | Route | Purpose | Key elements |\n| --- | --- | --- | --- |\n" + rows
                 if rows else "## Screens\n\n_None described._")
    parts.append("## Design principles\n\n" + _bullets(d.design_principles))
    parts.append("## Accessibility\n\n" + _bullets(d.accessibility))
    return "\n\n".join(p for p in parts if p).strip() + "\n"


def render_architecture(a: ArchitectureResult, references: list[dict], notes: list[str]) -> str:
    stack = "\n".join(
        f"| {_cell(s.layer)} | {_cell(s.choice)} | {_cell(s.reason)}"
        + (" " + " ".join(f"[{r}]" for r in s.reference_ids) if s.reference_ids else "")
        + f" | {_cell(', '.join(s.alternatives))} |"
        for s in a.stack
    )
    comps = "\n".join(f"| {_cell(c.name)} | {c.kind} | {_cell(c.responsibility)} |" for c in a.components)
    body = "\n\n".join([
        "# Architecture",
        a.summary,
        "## Technology stack\n\n| Layer | Choice | Why | Alternatives |\n| --- | --- | --- | --- |\n" + stack
        if stack else "## Technology stack\n\n_None given._",
        "## Components\n\n" + _mermaid(architecture_diagram(a))
        + ("\n\n| Component | Kind | Responsibility |\n| --- | --- | --- |\n" + comps if comps else ""),
        "## Data flow\n\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(a.data_flow, 1)) if a.data_flow
        else "## Data flow\n\n_Not described._",
        "## Deployment\n\n" + _bullets(a.deployment),
        "## Security\n\n" + _bullets(a.security),
        "## Scalability\n\n" + _bullets(a.scalability),
    ])
    return (body + _notes_section(notes) + _refs_footer(references, _used_refs(body))).strip() + "\n"


def render_schema(s: SchemaResult, references: list[dict], notes: list[str]) -> str:
    def keys(f) -> str:
        out = ["PK"] if f.pk else []
        if f.fk:
            out.append(f"FK → {f.fk}")
        out.append("required" if f.pk or not f.nullable else "nullable")
        return ", ".join(out)

    tables = []
    for e in s.entities:
        rows = "\n".join(
            f"| `{_cell(f.name)}` | {_cell(f.type)} | {keys(f)} | {_cell(f.note)} |" for f in e.fields
        )
        tables.append(f"### {e.name}\n\n{e.description}\n\n| Column | Type | Keys | Notes |\n| --- | --- | --- | --- |\n{rows}")
    rels = "\n".join(
        f"- **{r.source}** {r.cardinality.replace('_', ' ')} **{r.target}** ({r.label})" for r in s.relationships
    )
    body = "\n\n".join([
        "# Database schema",
        s.summary,
        "## Entity relationships\n\n" + _mermaid(er_diagram(s)),
        "## Tables\n\n" + ("\n\n".join(tables) if tables else "_No tables described._"),
        "## Relationships\n\n" + (rels or "_None described._"),
        "## Indexes\n\n" + _bullets(s.indexes),
        "## Notes\n\n" + _bullets(s.notes),
    ])
    return (body + _notes_section(notes) + _refs_footer(references, _used_refs(body))).strip() + "\n"


def render_api(api: ApiResult, references: list[dict], notes: list[str]) -> str:
    groups: dict[str, list] = {}
    for ep in api.endpoints:
        groups.setdefault(ep.group or "General", []).append(ep)
    sections = []
    for name, eps in groups.items():
        table = "\n".join(
            f"| `{ep.method}` | `{_cell(ep.path)}` | {_cell(ep.summary)} | {'yes' if ep.auth_required else 'no'} |"
            for ep in eps
        )
        details = "\n\n".join(
            f"#### `{ep.method} {ep.path}`\n\n{ep.summary}\n\n"
            + (f"- **Request:** {ep.request}\n" if ep.request else "")
            + (f"- **Response:** {ep.response}\n" if ep.response else "")
            + (f"- **Status codes:** {', '.join(ep.status_codes)}\n" if ep.status_codes else "")
            for ep in eps
        )
        sections.append(f"### {name}\n\n| Method | Path | Purpose | Auth |\n| --- | --- | --- | --- |\n{table}\n\n{details}")
    body = "\n\n".join([
        "# API specification",
        api.summary,
        f"**Base path:** `{api.base_path}`",
        "## Authentication\n\n" + (api.authentication or "_Not described._"),
        "## Endpoints\n\n" + ("\n\n".join(sections) if sections else "_None described._"),
        "## Errors\n\n" + (api.error_format or "_Not described._"),
        "## Conventions\n\n" + _bullets(api.conventions),
    ])
    return (body + _notes_section(notes) + _refs_footer(references, _used_refs(body))).strip() + "\n"


def render_prd(p: PrdResult, requirements: list[dict]) -> str:
    users = "\n".join(f"- **{u.name}**: {', '.join(u.needs) or 'needs not stated'}" for u in p.target_users)
    features = "\n".join(f"| {_cell(f.name)} | {f.priority} | {_cell(f.description)} |" for f in p.features)
    func = [r for r in requirements if r.get("kind") == "functional"]
    nonfunc = [r for r in requirements if r.get("kind") == "non_functional"]

    def req_table(rows: list[dict]) -> str:
        if not rows:
            return "_None stated._"
        return "| # | Requirement | Priority |\n| --- | --- | --- |\n" + "\n".join(
            f"| {i} | {_cell(r['text'])} | {r.get('priority', 'should')} |" for i, r in enumerate(rows, 1)
        )

    return "\n\n".join([
        "# Product requirements document",
        "## Overview\n\n" + (p.overview or "_Not stated._"),
        "## Problem\n\n" + (p.problem or "_Not stated._"),
        "## Goals\n\n" + _bullets(p.goals),
        "## Non-goals\n\n" + _bullets(p.non_goals),
        "## Target users\n\n" + (users or "_None stated._"),
        "## Scope\n\n**In scope**\n\n" + _bullets(p.scope_in) + "\n\n**Out of scope**\n\n" + _bullets(p.scope_out),
        "## Features\n\n| Feature | Priority | Description |\n| --- | --- | --- |\n" + features
        if features else "## Features\n\n_None stated._",
        "## Functional requirements\n\n" + req_table(func),
        "## Non-functional requirements\n\n" + req_table(nonfunc),
        "## Success metrics\n\n" + _bullets(p.success_metrics),
        "## Assumptions\n\n" + _bullets(p.assumptions),
        "## Risks\n\n" + _bullets(p.risks),
        "## Open questions\n\n" + _bullets(p.open_questions),
        "## Roadmap\n\nSee the Development roadmap section of this blueprint.",
    ]).strip() + "\n"


def render_roadmap(r: RoadmapResult) -> str:
    phases = []
    for i, ph in enumerate(r.phases, 1):
        tasks = "\n".join(
            f"| {_cell(t.title)} | {_cell(t.effort)} | {_cell(', '.join(t.depends_on))} |" for t in ph.tasks
        )
        phases.append(
            f"### Phase {i}: {ph.name}" + (f" ({ph.duration})" if ph.duration else "")
            + f"\n\n{ph.goal}\n\n"
            + ("| Task | Effort (estimate) | Depends on |\n| --- | --- | --- |\n" + tasks if tasks else "_No tasks._")
            + "\n\n**Deliverables**\n\n" + _bullets(ph.deliverables)
        )
    return "\n\n".join([
        "# Development roadmap",
        r.summary,
        "> Durations and efforts are rough estimates for planning, not commitments.",
        _mermaid(roadmap_diagram(r)),
        "## Phases\n\n" + ("\n\n".join(phases) if phases else "_No phases described._"),
        "## Milestones\n\n" + _bullets(r.milestones),
        "## Assumptions\n\n" + _bullets(r.assumptions),
    ]).strip() + "\n"
