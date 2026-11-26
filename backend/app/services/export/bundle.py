"""Everything one export contains, collected once and rendered as Markdown, PDF, Word or ZIP."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evaluation import Competitor
from app.models.project import Project, ProjectRequirement, ProjectVersion
from app.schemas.blueprint import ARTIFACT_TITLES
from app.services.blueprint.agent import latest_artifacts
from app.services.blueprint.render import _bullets, _cell
from app.services.export.reports import business_markdown, feasibility_markdown, latest_evaluation_for

# reading order of the blueprint in documents (generation order differs)
BLUEPRINT_ORDER = ("prd", "ui_ux", "architecture", "database_schema", "api_spec", "roadmap")
MISSING_TITLES = {**ARTIFACT_TITLES, "feasibility_report": "Feasibility report", "business_model": "Business model"}
DISCLAIMER = (
    "Scores are evidence-based estimates from the retrieved sources, not predictions of business "
    "success. Generated blueprints are starting points that need review by the team."
)


@dataclass
class Section:
    key: str
    title: str
    markdown: str
    note: str = ""  # e.g. "v3, edited by the user"


@dataclass
class ExportBundle:
    project: Project
    version: ProjectVersion
    generated_at: datetime
    overall_score: int | None
    sections: list[Section] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)  # machine-readable project.json

    @property
    def slug(self) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", self.project.title.lower()).strip("-")[:40] or "project"
        return f"ideaform-{base}-v{self.version.version_no}"


def _overview(project: Project, version: ProjectVersion, requirements: list[ProjectRequirement]) -> str:
    s = version.structured_idea or {}
    parts = [
        "# Idea and understanding",
        f"**Category:** {project.category} · **Help level:** {project.help_level} · **Version:** {version.version_no}",
        "## The idea as written",
        "\n".join(f"> {line}" if line.strip() else ">" for line in version.idea_text.strip().splitlines()),
    ]
    if s:
        parts += [
            "## Problem", s.get("problem") or "_Not stated._",
            "## Target users", _bullets([str(x) for x in s.get("target_users") or []]),
            "## Key features", _bullets([str(x) for x in s.get("key_features") or []]),
            "## Technologies mentioned", _bullets([str(x) for x in s.get("technologies_mentioned") or []]),
            "## Missing information", _bullets([str(x) for x in s.get("missing_information") or []], "Nothing flagged."),
        ]
    if requirements:
        parts.append(
            "## Requirements\n\n| # | Type | Priority | Requirement | Status |\n| --- | --- | --- | --- | --- |\n"
            + "\n".join(
                f"| {i} | {r.req_type.replace('_', ' ')} | {r.priority or 'should'} | {_cell(r.description)} | "
                f"{'confirmed' if r.confirmed else (r.source or 'extracted')} |"
                for i, r in enumerate(requirements, 1)
            )
        )
    return "\n\n".join(parts).strip() + "\n"


def collect(db: Session, project: Project, version: ProjectVersion) -> ExportBundle:
    requirements = db.scalars(
        select(ProjectRequirement).where(ProjectRequirement.version_id == version.id)
        .order_by(ProjectRequirement.confirmed.desc(), ProjectRequirement.created_at)
    ).all()
    evaluation = latest_evaluation_for(db, version.id)
    bundle = ExportBundle(
        project=project, version=version, generated_at=datetime.now(timezone.utc),
        overall_score=evaluation.overall_score if evaluation else None,
    )
    bundle.sections.append(Section("overview", "Idea and understanding", _overview(project, version, list(requirements))))
    if evaluation is not None:
        competitors = db.scalars(
            select(Competitor).where(Competitor.evaluation_id == evaluation.id).order_by(Competitor.name)
        ).all()
        bundle.sections.append(Section("feasibility_report", "Feasibility report",
                                       feasibility_markdown(project, version, evaluation, list(competitors))))
        bundle.sections.append(Section("business_model", "Business model",
                                       business_markdown(project, version, evaluation)))
    else:
        bundle.missing += ["feasibility_report", "business_model"]

    latest = latest_artifacts(db, version.id)
    for key in BLUEPRINT_ORDER:
        row = latest.get(key)
        if row is None:
            bundle.missing.append(key)
            continue
        note = f"v{row.artifact_version}" + (", edited by the user" if row.edited_by_user else "")
        bundle.sections.append(Section(key, ARTIFACT_TITLES[key], row.content, note))

    bundle.data = {
        "project": {"id": str(project.id), "title": project.title, "category": project.category,
                    "help_level": project.help_level},
        "version": {"id": str(version.id), "number": version.version_no, "idea_text": version.idea_text,
                    "structured_idea": version.structured_idea, "created_at": version.created_at},
        "requirements": [
            {"type": r.req_type, "priority": r.priority, "description": r.description,
             "source": r.source, "confirmed": r.confirmed} for r in requirements
        ],
        "evaluation": None if evaluation is None else {
            "id": str(evaluation.id), "overall_score": evaluation.overall_score, "summary": evaluation.summary,
            "model": evaluation.model_name, "prompt_version": evaluation.prompt_version,
            "dimensions": [
                {"dimension": d.dimension, "score": d.score, "confidence": d.confidence,
                 "explanation": d.explanation, "evidence_ids": d.evidence_ids, "claims": d.claims}
                for d in evaluation.dimensions
            ],
            "risks": evaluation.risks, "business_model": evaluation.business_model,
            "evidence": evaluation.evidence, "notices": evaluation.notices,
        },
        "artifacts": {
            k: {"version": latest[k].artifact_version, "edited_by_user": latest[k].edited_by_user,
                "data": latest[k].data}
            for k in BLUEPRINT_ORDER if k in latest
        },
        "missing": bundle.missing,
        "exported_at": bundle.generated_at,
        "disclaimer": DISCLAIMER,
    }
    return bundle


def shift_headings(markdown: str, by: int = 1) -> str:
    """Demote every heading outside code fences by ``by`` levels (max level 6)."""
    out, fenced = [], False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{1,6}\s", line):
            hashes = len(line) - len(line.lstrip("#"))
            line = "#" * min(6, hashes + by) + line[hashes:]
        out.append(line)
    return "\n".join(out)


def to_markdown(bundle: ExportBundle) -> str:
    """One self-contained Markdown document (diagrams stay as Mermaid code blocks)."""
    p, v = bundle.project, bundle.version
    toc = "\n".join(f"{i}. [{s.title}](#{re.sub(r'[^a-z0-9]+', '-', s.title.lower()).strip('-')})"
                    for i, s in enumerate(bundle.sections, 1))
    head = [
        f"# {p.title}",
        f"**IdeaForm project export** · version {v.version_no} · "
        f"{bundle.generated_at:%Y-%m-%d %H:%M} UTC"
        + (f" · overall score {bundle.overall_score}/100" if bundle.overall_score is not None else ""),
        f"> {DISCLAIMER}",
        "## Contents",
        toc,
    ]
    if bundle.missing:
        titles = {**ARTIFACT_TITLES, "feasibility_report": "Feasibility report", "business_model": "Business model"}
        head.append("_Not generated yet: " + ", ".join(titles.get(m, m.replace("_", " ")) for m in bundle.missing) + "._")
    body = []
    for s in bundle.sections:
        text = shift_headings(s.markdown, 1)
        lines = text.splitlines()
        if lines and lines[0].startswith("## "):
            lines[0] = f"## {s.title}" + (f" ({s.note})" if s.note else "")
        else:
            lines.insert(0, f"## {s.title}")
        body.append("\n".join(lines))
    return "\n\n".join(head) + "\n\n---\n\n" + "\n\n---\n\n".join(body) + "\n"


def to_json(bundle: ExportBundle) -> str:
    return json.dumps(bundle.data, indent=2, default=str, ensure_ascii=False)


def mermaid_blocks(markdown: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)\n```", markdown, flags=re.S)


__all__ = ["BLUEPRINT_ORDER", "DISCLAIMER", "ExportBundle", "Section", "collect", "mermaid_blocks",
           "shift_headings", "to_json", "to_markdown", "uuid"]
