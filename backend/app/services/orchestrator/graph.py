"""Full-analysis orchestrator (architecture.md 6, AI_DESIGN 6.7): one submission runs the
whole pipeline as a LangGraph ``StateGraph`` over a shared ``ProjectState``.

    understand -> research -> evaluate -> validate_evidence -+-> business -> product_design
                                 ^                            |        -> technical_architect
                                 +---- retry once ------------+        -> documentation -> finish

* Every agent step gets its own ``agent_runs`` row (``parent_run_id`` = the analysis run) with
  status, model, prompt version, tokens, timing and errors, so the UI can show progress.
* After each step its output is checked against the expected shape (schema validation). A
  failed or invalid step is retried once; if it fails again the pipeline continues and the
  step is listed in ``low_confidence`` (understanding is the only step that stops the run,
  because everything after it depends on the structured idea).
* After the evaluation, evidence validation re-checks every citation and claim label. Broken
  references send the graph back to the evaluation once; thin evidence is flagged.
* The project's help level decides how far the run goes; token and wall-clock budgets stop
  it early (remaining steps are marked skipped, finished work is kept).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.agent import AgentRun, ProjectArtifact
from app.models.evaluation import DIMENSIONS, Evaluation
from app.models.project import Project, ProjectVersion
from app.schemas.blueprint import BLUEPRINT_TYPES

logger = logging.getLogger(__name__)

STEPS = (
    "understanding", "research", "evaluation", "evidence_validation",
    "business", "product_design", "technical_architect", "documentation",
)
STEP_LABELS = {
    "understanding": "Understanding",
    "research": "Research Agent",
    "evaluation": "Evaluation Agent",
    "evidence_validation": "Evidence validation",
    "business": "Business Agent",
    "product_design": "Product Design Agent",
    "technical_architect": "Technical Architect Agent",
    "documentation": "Documentation Agent",
}
# which steps each help level runs (HELP_LEVELS in models/project.py)
DEPTH_STEPS = {
    "evaluate": {"understanding", "evaluation", "evidence_validation", "business", "documentation"},
    "research": {"understanding", "research", "evaluation", "evidence_validation", "business", "documentation"},
    "blueprint": set(STEPS),
    "everything": set(STEPS),
}
MAX_EVALUATION_RETRIES = 1


class ProjectState(TypedDict, total=False):
    """Shared state passed between nodes (architecture.md 6)."""

    project_id: str
    version_id: str
    depth: str
    category: str
    idea_summary: str
    requirements: int
    sources: int
    evidence: int
    evaluation_id: str
    overall_score: int | None
    business_model: bool
    artifacts: dict[str, int]
    steps: dict[str, dict]
    low_confidence: list[str]
    notices: list[str]
    errors: list[str]
    evaluation_retries: int
    evidence_issues: list[str]
    stopped: str | None
    status: str


def ordered_steps(steps: dict[str, dict]) -> list[dict]:
    """Steps as a list in pipeline order (JSONB does not keep dict key order)."""
    return [{"step": name, **steps[name]} for name in STEPS if name in steps]


class StepInvalid(RuntimeError):
    """The step finished but its output failed validation."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Orchestrator:
    def __init__(self, db: Session, parent: AgentRun, *, provider=None, search_provider=None,
                 crawler_factory=None) -> None:
        self.db = db
        self.parent = parent
        self.provider = provider
        self.search_provider = search_provider
        self.crawler_factory = crawler_factory
        self.started = time.monotonic()
        self.settings = get_settings()

    # ------------------------------------------------------------ helpers

    def project_version(self) -> tuple[Project, ProjectVersion]:
        project = self.db.get(Project, self.parent.project_id)
        version = self.db.get(ProjectVersion, self.parent.version_id)
        return project, version

    def tokens_used(self) -> int:
        total = self.db.scalar(
            select(func.coalesce(func.sum(func.coalesce(AgentRun.tokens_in, 0) + func.coalesce(AgentRun.tokens_out, 0)), 0))
            .where(AgentRun.parent_run_id == self.parent.id)
        )
        return int(total or 0)

    def over_budget(self) -> str | None:
        if self.tokens_used() >= self.settings.analysis_token_budget:
            return f"token budget of {self.settings.analysis_token_budget:,} reached"
        if time.monotonic() - self.started >= self.settings.analysis_max_seconds:
            return f"time budget of {self.settings.analysis_max_seconds} s reached"
        return None

    def _save_progress(self, state: ProjectState) -> None:
        """Mirror the state on the parent run so GET /runs/{id} shows live progress."""
        parent = self.db.get(AgentRun, self.parent.id)
        parent.output_ref = {
            "steps": ordered_steps(state.get("steps", {})),
            "low_confidence": state.get("low_confidence", []),
            "notices": state.get("notices", []),
            "errors": state.get("errors", []),
            "depth": state.get("depth"),
            "tokens": self.tokens_used(),
            "seconds": round(time.monotonic() - self.started, 1),
        }
        self.db.commit()

    def run_step(self, state: ProjectState, step: str, call: Callable[[uuid.UUID], Any],
                 check: Callable[[Any], list[str]], *, retries: int = 1) -> tuple[Any, dict]:
        """Run one agent step with its own tracked run, validation and one retry."""
        steps = dict(state.get("steps", {}))
        last_error = "unknown error"
        record: dict = {}
        for attempt in range(1, retries + 2):
            project, version = self.project_version()
            child = AgentRun(
                project_id=project.id,
                version_id=version.id,
                agent_name=step,
                status="queued",
                parent_run_id=self.parent.id,
                input_ref={"version_id": str(version.id), "attempt": attempt, "orchestrated": True},
            )
            self.db.add(child)
            self.db.commit()
            steps[step] = {"status": "running", "run_id": str(child.id), "attempt": attempt,
                           "label": STEP_LABELS[step]}
            self._save_progress({**state, "steps": steps})
            started = time.monotonic()
            try:
                output = call(child.id)
                issues = check(output)
                if issues:
                    raise StepInvalid("; ".join(issues))
                child = self.db.get(AgentRun, child.id)
                if child.status in ("queued", "running"):
                    child.status = "succeeded"
                    child.started_at = child.started_at or _utcnow()
                    child.finished_at = _utcnow()
                    child.output_ref = child.output_ref or (output if isinstance(output, dict) else None)
                    self.db.commit()
                record = {"status": "succeeded", "run_id": str(child.id), "attempt": attempt,
                          "label": STEP_LABELS[step], "seconds": round(time.monotonic() - started, 1)}
                steps[step] = record
                return output, {**state, "steps": steps}
            except Exception as exc:  # noqa: BLE001 - recorded, retried, then flagged
                self.db.rollback()
                last_error = str(exc)[:500]
                logger.warning("step %s attempt %s failed: %s", step, attempt, last_error)
                failed = self.db.get(AgentRun, child.id)
                if failed is not None:
                    failed.status = "failed"
                    failed.finished_at = _utcnow()
                    prefix = "validation: " if isinstance(exc, StepInvalid) else ""
                    failed.error_message = (failed.error_message or f"{prefix}{last_error}")[:2_000]
                    self.db.commit()
                project, _ = self.project_version()
                if project.status == "failed" and project.current_version_id:
                    version = self.db.get(ProjectVersion, project.current_version_id)
                    project.status = "analysing" if version and version.structured_idea else project.status
                    self.db.commit()
        record = {"status": "failed", "run_id": steps.get(step, {}).get("run_id"), "attempt": retries + 1,
                  "label": STEP_LABELS[step], "error": last_error}
        steps[step] = record
        flagged = list(state.get("low_confidence", [])) + [step]
        errors = list(state.get("errors", [])) + [f"{STEP_LABELS[step]}: {last_error}"]
        return None, {**state, "steps": steps, "low_confidence": flagged, "errors": errors}

    def skip(self, state: ProjectState, step: str, reason: str) -> ProjectState:
        steps = dict(state.get("steps", {}))
        steps[step] = {"status": "skipped", "label": STEP_LABELS[step], "reason": reason}
        return {**state, "steps": steps}

    # ------------------------------------------------------------ nodes

    def understand(self, state: ProjectState) -> ProjectState:
        from app.services.nlp.pipeline import run_understanding

        project, version = self.project_version()
        if version.structured_idea:
            state = self.skip(state, "understanding", "already understood (reused, no tokens)")
        else:
            def check(out) -> list[str]:
                _, v = self.project_version()
                self.db.refresh(v)
                return [] if v.structured_idea else ["no structured idea was stored"]

            _, state = self.run_step(state, "understanding", lambda rid: run_understanding(self.db, project.id, rid), check)
            if state["steps"]["understanding"]["status"] == "failed":
                return {**state, "stopped": "understanding failed, so nothing after it can run"}
        project, version = self.project_version()
        self.db.refresh(version)
        s = version.structured_idea or {}
        if (s.get("clarity") or {}).get("vague"):
            state = {
                **state,
                "low_confidence": list(state.get("low_confidence", [])) + ["understanding"],
                "notices": list(state.get("notices", [])) + [
                    "The idea is vague, so every later step rests on assumptions. Answer the clarifying "
                    "questions on the Understanding tab and run the analysis again."
                ],
            }
        return {
            **state,
            "category": s.get("category") or project.category,
            "idea_summary": (s.get("problem") or version.idea_text)[:300],
        }

    def research(self, state: ProjectState) -> ProjectState:
        from app.services.research.agent import run_research

        project, _ = self.project_version()

        def call(rid):
            return run_research(self.db, project.id, rid, provider=self.search_provider,
                                crawler_factory=self.crawler_factory)

        out, state = self.run_step(state, "research", call, lambda out: [] if isinstance(out, dict) else ["no result"])
        if out is not None:
            stored = int(out.get("sources_stored") or out.get("sources") or out.get("stored") or 0)
            state = {**state, "sources": stored}
            if stored == 0:
                notices = list(state.get("notices", [])) + [
                    "Research stored no new sources; the evaluation relies on the knowledge bases and uploads."
                ]
                state = {**state, "notices": notices, "low_confidence": list(state.get("low_confidence", [])) + ["research"]}
        return state

    def evaluate(self, state: ProjectState) -> ProjectState:
        from app.services.evaluation.agent import run_evaluation

        project, _ = self.project_version()

        def check(out) -> list[str]:
            evaluation = self.db.get(Evaluation, uuid.UUID(out["evaluation_id"])) if out else None
            if evaluation is None:
                return ["no evaluation was stored"]
            got = {d.dimension: d.score for d in evaluation.dimensions}
            issues = [f"dimension {k} missing" for k in DIMENSIONS if k not in got]
            issues += [f"{k} score {v} outside 0-100" for k, v in got.items() if not 0 <= v <= 100]
            return issues

        kwargs = {"provider": self.provider} if self.provider else {}
        out, state = self.run_step(state, "evaluation", lambda rid: run_evaluation(self.db, project.id, rid, **kwargs), check)
        if out is None:
            return state
        return {**state, "evaluation_id": out["evaluation_id"], "overall_score": out.get("overall_score"),
                "evidence": int(out.get("evidence") or 0)}

    def validate_evidence(self, state: ProjectState) -> ProjectState:
        """Evidence validation node (AI_DESIGN 6.7): citations exist, facts are cited."""
        from app.services.evaluation.agent import MIN_EVIDENCE

        if not state.get("evaluation_id"):
            return self.skip(state, "evidence_validation", "no evaluation to validate")

        def call(_rid):
            evaluation = self.db.get(Evaluation, uuid.UUID(state["evaluation_id"]))
            valid = {e.get("id") for e in (evaluation.evidence or []) if isinstance(e, dict)}
            broken, uncited = [], []
            for d in evaluation.dimensions:
                broken += [f"{d.dimension}:{ref}" for ref in (d.evidence_ids or []) if ref not in valid]
                for c in d.claims or []:
                    if isinstance(c, dict) and c.get("label") == "verified_fact":
                        refs = c.get("evidence_ids") or []
                        if not refs:
                            uncited.append(d.dimension)
                        broken += [f"{d.dimension}:{r}" for r in refs if r not in valid]
            return {"evidence": len(valid), "broken_references": broken, "uncited_facts": uncited,
                    "thin_evidence": len(valid) < MIN_EVIDENCE}

        out, state = self.run_step(state, "evidence_validation", call, lambda out: [], retries=0)
        issues = (out or {}).get("broken_references", []) + [f"uncited fact in {d}" for d in (out or {}).get("uncited_facts", [])]
        state = {**state, "evidence_issues": issues}
        if out and out.get("thin_evidence") and "evaluation" not in state.get("low_confidence", []):
            state = {
                **state,
                "low_confidence": list(state.get("low_confidence", [])) + ["evaluation"],
                "notices": list(state.get("notices", [])) + [
                    f"Only {out['evidence']} evidence passages were found, so the scores are low confidence."
                ],
            }
        return state

    def business(self, state: ProjectState) -> ProjectState:
        """Business Agent: make sure the evaluation carries a business model (rebuild once if not)."""
        if not state.get("evaluation_id"):
            return self.skip(state, "business", "no evaluation")

        def call(rid):
            from app.services.evaluation import evaluator
            from app.services.evaluation.evidence import EvidenceItem, EvidenceSet, validate_ids_on
            from app.services.llm import get_llm

            evaluation = self.db.get(Evaluation, uuid.UUID(state["evaluation_id"]))
            if evaluation.business_model:
                return {"business_model": "from evaluation", "reused": True}
            project, version = self.project_version()
            run = self.db.get(AgentRun, rid)
            run.status, run.started_at = "running", _utcnow()
            self.db.commit()
            items = [
                EvidenceItem(id=e["id"], chunk_id=str(e.get("chunk_id") or ""), source_id=str(e.get("source_id") or ""),
                             kb=e.get("kb") or "C", title=e.get("title"), url=e.get("url"),
                             publisher=e.get("publisher"), published_at=e.get("published_at"),
                             content=e.get("snippet") or "")
                for e in (evaluation.evidence or []) if isinstance(e, dict) and e.get("id")
            ]
            evidence = EvidenceSet(items=items, groups={"business_model": [i.id for i in items]})
            usage = evaluator.Usage()
            idea = evaluator.idea_block(project.title, version.structured_idea, version.idea_text)
            result = evaluator.analyse_business(self.provider or get_llm(), idea, evidence, usage)
            validate_ids_on([result], evidence)
            evaluation.business_model = result.model_dump()
            run.model_name, run.tokens_in, run.tokens_out = usage.model, usage.tokens_in, usage.tokens_out
            self.db.commit()
            return {"business_model": "rebuilt"}

        def check(out) -> list[str]:
            evaluation = self.db.get(Evaluation, uuid.UUID(state["evaluation_id"]))
            self.db.refresh(evaluation)
            bm = evaluation.business_model or {}
            return [] if bm.get("value_proposition") or bm.get("revenue_streams") else ["business model is empty"]

        out, state = self.run_step(state, "business", call, check)
        return {**state, "business_model": out is not None}

    def _blueprint(self, state: ProjectState, step: str, types: list[str]) -> ProjectState:
        from app.services.blueprint.agent import latest_artifacts, run_blueprint

        project, version = self.project_version()
        kwargs = {"provider": self.provider} if self.provider else {}

        def check(out) -> list[str]:
            latest = latest_artifacts(self.db, version.id)
            issues = [f"{t} was not stored" for t in types if t not in latest]
            issues += [f"{t} is empty" for t in types if t in latest and len(latest[t].content.strip()) < 40]
            return issues

        out, state = self.run_step(state, step, lambda rid: run_blueprint(self.db, project.id, rid, types=types, **kwargs), check)
        if out is not None:
            state = {**state, "artifacts": {**state.get("artifacts", {}), **out.get("sections", {})}}
        return state

    def product_design(self, state: ProjectState) -> ProjectState:
        return self._blueprint(state, "product_design", ["ui_ux"])

    def technical_architect(self, state: ProjectState) -> ProjectState:
        return self._blueprint(state, "technical_architect", ["architecture", "database_schema", "api_spec"])

    def documentation(self, state: ProjectState) -> ProjectState:
        """Documentation Agent: PRD and roadmap (by depth), then the feasibility and business reports."""
        from app.services.blueprint.agent import run_blueprint
        from app.services.export.reports import build_reports

        project, version = self.project_version()
        depth = state.get("depth", "everything")
        types = []
        if depth in ("blueprint", "everything"):
            types = ["prd", "roadmap"] if depth == "everything" else ["prd"]
        kwargs = {"provider": self.provider} if self.provider else {}

        def call(rid):
            made: dict[str, int] = {}
            if types:
                made.update(run_blueprint(self.db, project.id, rid, types=types, **kwargs)["sections"])
            p, v = self.project_version()
            made.update(build_reports(self.db, p, v, run_id=rid))
            return {"sections": made}

        def check(out) -> list[str]:
            made = (out or {}).get("sections", {})
            issues = [f"{t} was not stored" for t in types if t not in made]
            if state.get("evaluation_id") and "feasibility_report" not in made:
                issues.append("feasibility report was not stored")
            return issues

        out, state = self.run_step(state, "documentation", call, check)
        if out is not None:
            state = {**state, "artifacts": {**state.get("artifacts", {}), **out["sections"]}}
        return state

    # ------------------------------------------------------------ graph

    def guarded(self, step: str, node: Callable[[ProjectState], ProjectState]):
        """Wrap a node: skip it when the depth excludes it, the run stopped, or a budget ran out."""
        def wrapped(state: ProjectState) -> ProjectState:
            if state.get("stopped"):
                return self.skip(state, step, state["stopped"])
            if step not in DEPTH_STEPS.get(state.get("depth", "everything"), set(STEPS)):
                out = self.skip(state, step, f"not part of the '{state.get('depth')}' help level")
                self._save_progress(out)
                return out
            reason = self.over_budget()
            if reason:
                out = self.skip({**state, "stopped": reason}, step, reason)
                out["notices"] = list(out.get("notices", [])) + [f"Stopped early: {reason}. Finished steps are kept."]
                self._save_progress(out)
                return out
            out = node(state)
            self._save_progress(out)
            return out
        return wrapped

    def after_validation(self, state: ProjectState) -> str:
        if (state.get("evidence_issues") and state.get("evaluation_retries", 0) < MAX_EVALUATION_RETRIES
                and not state.get("stopped")):
            return "retry"
        return "continue"

    def count_retry(self, state: ProjectState) -> ProjectState:
        flagged = list(state.get("low_confidence", []))
        notices = list(state.get("notices", [])) + [
            "Evidence validation found broken references, so the evaluation was run again."
        ]
        return {**state, "evaluation_retries": state.get("evaluation_retries", 0) + 1,
                "low_confidence": flagged, "notices": notices}

    def build(self):
        graph = StateGraph(ProjectState)
        graph.add_node("understand", self.guarded("understanding", self.understand))
        graph.add_node("research", self.guarded("research", self.research))
        graph.add_node("evaluate", self.guarded("evaluation", self.evaluate))
        graph.add_node("validate_evidence", self.guarded("evidence_validation", self.validate_evidence))
        graph.add_node("retry_evaluation", self.count_retry)
        graph.add_node("business", self.guarded("business", self.business))
        graph.add_node("product_design", self.guarded("product_design", self.product_design))
        graph.add_node("technical_architect", self.guarded("technical_architect", self.technical_architect))
        graph.add_node("documentation", self.guarded("documentation", self.documentation))
        graph.add_edge(START, "understand")
        graph.add_edge("understand", "research")
        graph.add_edge("research", "evaluate")
        graph.add_edge("evaluate", "validate_evidence")
        graph.add_conditional_edges("validate_evidence", self.after_validation,
                                    {"retry": "retry_evaluation", "continue": "business"})
        graph.add_edge("retry_evaluation", "evaluate")
        graph.add_edge("business", "product_design")
        graph.add_edge("product_design", "technical_architect")
        graph.add_edge("technical_architect", "documentation")
        graph.add_edge("documentation", END)
        return graph.compile()


def run_analysis(
    db: Session,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    *,
    depth: str | None = None,
    provider=None,
    search_provider=None,
    crawler_factory=None,
) -> dict:
    """Run the whole pipeline for the project's current version under the analysis run ``run_id``."""
    parent = db.get(AgentRun, run_id)
    project = db.get(Project, project_id)
    if parent is None or project is None:
        raise ValueError("analysis run or project not found")
    if parent.version_id is None:
        parent.version_id = project.current_version_id
    parent.status, parent.started_at = "running", _utcnow()
    project.status = "analysing"
    db.commit()

    orchestrator = Orchestrator(db, parent, provider=provider, search_provider=search_provider,
                                crawler_factory=crawler_factory)
    state: ProjectState = {
        "project_id": str(project.id),
        "version_id": str(parent.version_id),
        "depth": depth or project.help_level or "everything",
        "steps": {}, "low_confidence": [], "notices": [], "errors": [], "artifacts": {},
        "evaluation_retries": 0, "stopped": None,
    }
    try:
        final: ProjectState = orchestrator.build().invoke(state, {"recursion_limit": 40})
    except Exception as exc:  # noqa: BLE001 - unexpected graph error: record it, keep finished work
        logger.exception("analysis failed for %s", project_id)
        db.rollback()
        parent = db.get(AgentRun, run_id)
        parent.status, parent.finished_at = "failed", _utcnow()
        parent.error_message = str(exc)[:2_000]
        project = db.get(Project, project_id)
        project.status = "ready" if project.status == "analysing" else project.status
        db.commit()
        raise

    tokens_in, tokens_out = db.execute(
        select(func.coalesce(func.sum(AgentRun.tokens_in), 0), func.coalesce(func.sum(AgentRun.tokens_out), 0))
        .where(AgentRun.parent_run_id == run_id)
    ).one()
    models = db.scalars(
        select(AgentRun.model_name).where(AgentRun.parent_run_id == run_id).where(AgentRun.model_name.is_not(None)).distinct()
    ).all()
    understood = final["steps"].get("understanding", {}).get("status") != "failed"
    summary = {
        "steps": ordered_steps(final.get("steps", {})),
        "depth": final.get("depth"),
        "evaluation_id": final.get("evaluation_id"),
        "overall_score": final.get("overall_score"),
        "evidence": final.get("evidence"),
        "sources": final.get("sources"),
        "artifacts": final.get("artifacts", {}),
        "low_confidence": sorted(set(final.get("low_confidence", []))),
        "notices": final.get("notices", []),
        "errors": final.get("errors", []),
        "stopped": final.get("stopped"),
        "tokens": int(tokens_in) + int(tokens_out),
        "seconds": round(time.monotonic() - orchestrator.started, 1),
    }
    parent = db.get(AgentRun, run_id)
    parent.status = "succeeded" if understood else "failed"
    parent.finished_at = _utcnow()
    parent.tokens_in, parent.tokens_out = int(tokens_in), int(tokens_out)
    parent.model_name = ", ".join(sorted(models)) or None
    parent.prompt_version = "orchestrator/v1"
    parent.output_ref = summary
    if not understood:
        parent.error_message = "; ".join(final.get("errors", []))[:2_000]
    project = db.get(Project, project_id)
    project.status = "ready" if understood else "failed"
    db.commit()
    return summary


def artifact_counts(db: Session, version_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(ProjectArtifact.artifact_type, func.max(ProjectArtifact.artifact_version))
        .where(ProjectArtifact.version_id == version_id).group_by(ProjectArtifact.artifact_type)
    ).all()
    return {t: v for t, v in rows if t in BLUEPRINT_TYPES or t in ("feasibility_report", "business_model")}
