"""Phase 5 through the API: full analysis graph, validation and retries, budgets, run
tracking, reports, version history, export and the content-hash cache (DB tests)."""

from __future__ import annotations

import io
import zipfile

import pytest
from sqlalchemy import select

from app.models.agent import AgentRun, LLMCache, ProjectArtifact
from tests.blueprint_fakes import FakeBlueprintProvider
from tests.conftest import register_and_login
from tests.evaluation_fakes import FakeEvalProvider

STEPS = ["understanding", "research", "evaluation", "evidence_validation",
         "business", "product_design", "technical_architect", "documentation"]
URLS = ["https://tutors.test/market", "https://reviews.test/tutors"]


@pytest.fixture
def fakes(monkeypatch, fake_llm):
    """Every agent on fakes: NLP, research (search + crawler), evaluation, blueprint."""
    from app.services.blueprint import agent as blueprint_agent
    from app.services.evaluation import agent as eval_agent
    from app.services.research import agent as research_agent
    from app.services.scrapers.crawler import Crawler
    from tests.test_research import FakeFetcher, FakeProvider, FakeRobots, _page

    evaluation = FakeEvalProvider(bump=0)
    blueprint = FakeBlueprintProvider()
    monkeypatch.setattr(eval_agent, "get_llm", lambda: evaluation)
    monkeypatch.setattr(eval_agent, "_lookup_websites", lambda *a, **k: {})
    monkeypatch.setattr(blueprint_agent, "get_llm", lambda: blueprint)
    monkeypatch.setattr("app.services.llm.get_llm", lambda: evaluation)

    fetcher = FakeFetcher({URLS[0]: _page("Tutor market size"), URLS[1]: _page("Tutor reviews compared")})
    monkeypatch.setattr(research_agent, "get_search_provider", lambda: FakeProvider(URLS))
    real = research_agent.run_research

    def research(*a, **k):
        k.pop("crawler_factory", None)
        k.pop("provider", None)
        return real(*a, crawler_factory=lambda *x, **y: Crawler(*x, robots=FakeRobots(), fetcher=fetcher, **y), **k)

    monkeypatch.setattr(research_agent, "run_research", research)
    return {"evaluation": evaluation, "blueprint": blueprint}


def _analyse(client, auth, project, **body):
    r = client.post(f"/projects/{project['id']}/analyse", json=body or None, headers=auth)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "queued"
    run = client.get(f"/runs/{r.json()['run_id']}", headers=auth)  # background task already ran
    assert run.status_code == 200, run.text
    return run.json()


def _steps(run):
    return {s["step"]: s for s in run["output"]["steps"]}


def test_one_submission_runs_every_agent_and_exports(client, auth, project, fakes, db_session):
    run = _analyse(client, auth, project)
    assert run["status"] == "succeeded" and run["agent_name"] == "analysis"
    assert run["prompt_version"] == "orchestrator/v1" and run["duration_seconds"] is not None
    steps = _steps(run)
    assert list(steps) == STEPS
    assert all(s["status"] == "succeeded" for s in steps.values()), steps
    # every step is its own tracked run under the analysis run
    children = run["steps"]
    assert [c["agent_name"] for c in children] == STEPS
    assert all(c["parent_run_id"] == run["id"] and c["status"] == "succeeded" for c in children)
    assert run["tokens_in"] == sum(c["tokens_in"] or 0 for c in children) > 0
    assert run["output"]["sources"] == 2 and run["output"]["overall_score"] is not None

    pid = project["id"]
    blueprint = client.get(f"/projects/{pid}/artifacts", headers=auth).json()
    assert blueprint["missing"] == []
    reports = client.get(f"/projects/{pid}/reports", headers=auth).json()
    assert [r["artifact_type"] for r in reports["reports"]] == ["feasibility_report", "business_model"]
    assert "Competitor analysis" in reports["reports"][0]["content"]

    pdf = client.post(f"/projects/{pid}/export?format=pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF") and 'filename="ideaform-tutor-finder-v1.pdf"' in pdf.headers["content-disposition"]
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf.content))
    text = "".join(p.extract_text() for p in reader.pages)
    assert len(reader.pages) >= 8 and "Feasibility report" in text and "Database schema" in text

    archive = client.post(f"/projects/{pid}/export?format=zip", headers=auth)
    assert archive.status_code == 200 and archive.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(archive.content)).namelist()
    root = "ideaform-tutor-finder-v1/"
    for name in ("report.pdf", "report.docx", "report.md", "data/project.json", "README.txt",
                 "sections/02-feasibility_report.md", "sections/06-architecture.md"):
        assert root + name in names, name
    assert any(n.startswith(root + "diagrams/") and n.endswith(".mmd") for n in names)

    md = client.post(f"/projects/{pid}/export?format=md", headers=auth)
    assert md.status_code == 200 and "## Feasibility report" in md.text and "```mermaid" in md.text
    docx = client.post(f"/projects/{pid}/export?format=docx", headers=auth)
    from docx import Document

    headings = [p.text for p in Document(io.BytesIO(docx.content)).paragraphs if p.style.name.startswith("Heading")]
    assert "Feasibility report" in headings and "Architecture" in headings

    exports = db_session.scalars(select(AgentRun).where(AgentRun.agent_name == "export")).all()
    assert sorted(e.input_ref["format"] for e in exports) == ["docx", "md", "pdf", "zip"]


def test_help_level_decides_how_far_the_run_goes(client, auth, project, fakes):
    run = _analyse(client, auth, project, depth="evaluate")
    steps = _steps(run)
    for skipped in ("research", "product_design", "technical_architect"):
        assert steps[skipped]["status"] == "skipped" and "evaluate" in steps[skipped]["reason"]
    assert steps["documentation"]["status"] == "succeeded"
    pid = project["id"]
    assert client.get(f"/projects/{pid}/artifacts", headers=auth).json()["artifacts"] == []
    assert len(client.get(f"/projects/{pid}/reports", headers=auth).json()["reports"]) == 2
    assert fakes["blueprint"].calls == []


def test_failed_step_is_retried_once_then_flagged(client, auth, project, fakes, db_session):
    fakes["blueprint"].fail_on = "ApiResult"
    run = _analyse(client, auth, project)
    steps = _steps(run)
    assert run["status"] == "succeeded"  # the pipeline continued
    assert steps["technical_architect"]["status"] == "failed" and steps["technical_architect"]["attempt"] == 2
    assert "technical_architect" in run["output"]["low_confidence"]
    assert any("Technical Architect Agent" in e for e in run["output"]["errors"])
    attempts = db_session.scalars(
        select(AgentRun).where(AgentRun.agent_name == "technical_architect").order_by(AgentRun.started_at)
    ).all()
    assert [a.status for a in attempts] == ["failed", "failed"]
    assert all("model unavailable" in a.error_message for a in attempts)
    assert steps["documentation"]["status"] == "succeeded"  # later steps still ran
    missing = client.get(f"/projects/{project['id']}/artifacts", headers=auth).json()["missing"]
    assert "api_spec" in missing and "prd" not in missing


def test_broken_evidence_sends_the_graph_back_to_evaluation_once(client, auth, project, fakes, monkeypatch):
    from app.services.orchestrator.graph import Orchestrator

    real = Orchestrator.validate_evidence
    calls = {"n": 0}

    def flaky(self, state):
        calls["n"] += 1
        out = real(self, state)
        return {**out, "evidence_issues": ["evaluation:E99"]} if calls["n"] == 1 else out

    monkeypatch.setattr(Orchestrator, "validate_evidence", flaky)
    run = _analyse(client, auth, project, depth="evaluate")
    assert calls["n"] == 2
    assert [c["agent_name"] for c in run["steps"]].count("evaluation") == 2
    assert any("run again" in n for n in run["output"]["notices"])


def test_understanding_failure_stops_the_run(client, auth, project, fakes, monkeypatch, fake_llm):
    from app.services.llm.base import LLMError
    from app.services.nlp import pipeline

    def boom(*a, **k):
        raise LLMError("model unavailable")

    monkeypatch.setattr(pipeline, "classify_idea", boom)
    run = _analyse(client, auth, project)
    steps = _steps(run)
    assert run["status"] == "failed" and steps["understanding"]["status"] == "failed"
    assert all(steps[s]["status"] == "skipped" for s in STEPS[1:])
    assert "model unavailable" in run["error_message"]


def test_token_budget_stops_early_and_keeps_finished_work(client, auth, project, fakes, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "analysis_token_budget", 1)
    run = _analyse(client, auth, project)
    steps = _steps(run)
    assert steps["understanding"]["status"] == "succeeded"
    assert all(steps[s]["status"] == "skipped" and "token budget" in steps[s]["reason"] for s in STEPS[1:])
    assert any("Stopped early" in n for n in run["output"]["notices"])


def test_one_analysis_at_a_time(client, auth, project, db_session):
    from app.models.project import Project

    proj = db_session.get(Project, project["id"])
    from datetime import datetime, timezone

    db_session.add(AgentRun(project_id=proj.id, version_id=proj.current_version_id, agent_name="analysis",
                            status="running", started_at=datetime.now(timezone.utc)))
    db_session.commit()
    r = client.post(f"/projects/{project['id']}/analyse", headers=auth)
    assert r.status_code == 409 and "already running" in r.json()["detail"]


def test_history_reports_and_ownership(client, auth, project, fakes, db_session):
    _analyse(client, auth, project, depth="blueprint")
    pid = project["id"]
    client.post(f"/projects/{pid}/export?format=md", headers=auth)

    history = client.get(f"/projects/{pid}/history", headers=auth).json()
    v1 = history["versions"][0]
    assert v1["version_no"] == 1 and v1["is_current"] and v1["understood"]
    assert v1["evaluations"] and v1["evaluations"][0]["overall_score"] is not None
    types = {a["artifact_type"] for a in v1["artifacts"]}
    assert {"ui_ux", "architecture", "database_schema", "api_spec", "prd", "feasibility_report", "business_model"} <= types
    assert "roadmap" not in types  # the blueprint help level writes the PRD but not the roadmap
    agents = [r["agent_name"] for r in history["runs"]]
    assert "analysis" in agents and "export" in agents
    assert "technical_architect" not in agents  # child steps are listed under their analysis run

    # rebuilding unchanged reports does not add versions
    before = db_session.query(ProjectArtifact).filter(ProjectArtifact.artifact_type == "feasibility_report").count()
    assert client.post(f"/projects/{pid}/reports", headers=auth).status_code == 201
    after = db_session.query(ProjectArtifact).filter(ProjectArtifact.artifact_type == "feasibility_report").count()
    assert before == after == 1

    other = register_and_login(client, "mallory@example.com")
    for method, path in (("post", f"/projects/{pid}/analyse"), ("get", f"/projects/{pid}/history"),
                         ("get", f"/projects/{pid}/reports"), ("post", f"/projects/{pid}/export?format=pdf")):
        assert getattr(client, method)(path, headers=other).status_code == 404


def test_export_before_evaluation_lists_what_is_missing(client, auth, project):
    r = client.post(f"/projects/{project['id']}/export?format=md", headers=auth)
    assert r.status_code == 200
    assert "Not generated yet" in r.text and "Feasibility report" in r.text
    assert client.post(f"/projects/{project['id']}/export?format=exe", headers=auth).status_code == 422
    assert client.post(f"/projects/{project['id']}/reports", headers=auth).status_code == 409


def test_content_hash_cache_answers_repeat_extraction_without_tokens(db_session):
    from app.schemas.nlp import IdeaClassification
    from app.services.llm import ChatMessage, generate_json
    from app.services.llm.base import LLMResult, LLMTier
    from app.services.llm.cache import get_cache

    get_cache.cache_clear()

    class Counting:
        name = "counting"
        fast_model = "fast"
        strong_model = "strong"
        calls = 0

        def complete(self, messages, **kw):
            Counting.calls += 1
            return LLMResult(text='{"category": "software", "confidence": "high", "rationale": "an app"}',
                             model="fast", tokens_in=30, tokens_out=10)

    msgs = [ChatMessage.system("classify"), ChatMessage.user("IDEA: a tutoring app")]
    first, r1 = generate_json(Counting(), msgs, IdeaClassification, tier=LLMTier.FAST, cache=True)
    second, r2 = generate_json(Counting(), msgs, IdeaClassification, tier=LLMTier.FAST, cache=True)
    assert Counting.calls == 1 and first == second
    assert (r1.tokens_in, r2.tokens_in, r2.tokens_out) == (30, 0, 0)
    row = db_session.scalars(select(LLMCache)).one()
    assert row.hits == 1 and len(row.cache_key) == 64
    # a different idea is a different key
    generate_json(Counting(), [msgs[0], ChatMessage.user("IDEA: a drone")], IdeaClassification,
                  tier=LLMTier.FAST, cache=True)
    assert Counting.calls == 2
    # without cache=True nothing is cached or reused
    generate_json(Counting(), msgs, IdeaClassification, tier=LLMTier.FAST)
    assert Counting.calls == 3
