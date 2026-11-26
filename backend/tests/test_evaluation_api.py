"""Phase 3 through the API: evaluate, list, improvement loop, compare (DB tests).

The LLM is a schema-aware fake (``tests/evaluation_fakes.py``); retrieval runs for real
over an uploaded KB-C document with the hashing embedder.
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy import func, select

from app.models.agent import AgentRun
from app.models.evaluation import EvaluationEvidence
from app.models.project import ProjectFeedback
from app.services.llm.base import LLMError
from tests.conftest import register_and_login
from tests.evaluation_fakes import SCORES, FakeEvalProvider

DOC = " ".join(
    f"Interview {i}: university students said affordable peer tutors and verified reviews matter "
    "more than price; TutorHub and similar marketplaces charge tutors a commission per session."
    for i in range(40)
)


@pytest.fixture
def fake_eval(monkeypatch, fake_llm):
    from app.services.evaluation import agent, improve

    provider = FakeEvalProvider(bump=8)
    monkeypatch.setattr(agent, "get_llm", lambda: provider)
    monkeypatch.setattr(improve, "get_llm", lambda: provider)
    monkeypatch.setattr(agent, "_lookup_websites", lambda *a, **k: {})
    return provider


def _with_evidence(client, auth, project):
    r = client.post(
        f"/projects/{project['id']}/documents",
        files={"file": ("interviews.txt", io.BytesIO(DOC.encode()), "text/plain")},
        headers=auth,
    )
    assert r.status_code == 201, r.text


def _evaluate(client, auth, project):
    r = client.post(f"/projects/{project['id']}/evaluate", headers=auth)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "succeeded"
    r = client.get(f"/projects/{project['id']}/evaluations", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()[0]


def test_evaluate_builds_validated_six_dimension_evaluation(client, auth, project, fake_eval, db_session):
    _with_evidence(client, auth, project)
    ev = _evaluate(client, auth, project)

    assert ev["version_no"] == 1 and "not predictions" in ev["disclaimer"]
    assert [d["dimension"] for d in ev["dimensions"]] == list(SCORES)
    assert ev["overall_score"] == round(sum(SCORES.values()) / 6)
    valid = {e["id"] for e in ev["evidence"]}
    assert valid and all(e["url"] is None or e["url"].startswith("http") for e in ev["evidence"])
    for dim in ev["dimensions"]:
        assert set(dim["evidence_ids"]) <= valid and "[E99]" not in dim["explanation"]
        labels = {c["label"] for c in dim["claims"]}
        assert labels == {"verified_fact", "assumption", "ai_suggestion"}
        assert any("40% a year" in a for a in dim["assumptions"])  # relabelled
        assert all(c["evidence_ids"] for c in dim["claims"] if c["label"] == "verified_fact")
        assert dim["change_reason"] is None and dim["previous_score"] is None
    assert any("does not exist" in n for n in ev["notices"])

    assert [c["name"] for c in ev["competitors"]] == ["TutorHub"]  # uncited one dropped
    assert ev["competitors"][0]["website"] is None  # its domain is not in the evidence
    assert len(ev["risks"]) == 2 and ev["devils_advocate"]
    assert ev["critique"]["must_be_true"] and ev["alternatives"]
    assert all(i["id"] and i["dimension_affected"] for i in ev["improvements"])
    assert ev["business_model"]["revenue_streams"] == ["Commission"]

    links = db_session.scalar(select(func.count()).select_from(EvaluationEvidence))
    assert links > 0
    run = db_session.scalar(select(AgentRun).where(AgentRun.agent_name == "evaluation"))
    assert run.status == "succeeded" and run.prompt_version == "evaluation/v1" and run.tokens_in > 0
    # the project had no structure yet, so understanding ran first on its own run
    assert db_session.scalar(select(AgentRun).where(AgentRun.agent_name == "understanding"))


def test_improvement_loop_creates_version_and_explained_comparison(
    client, auth, project, fake_eval, db_session
):
    _with_evidence(client, auth, project)
    ev = _evaluate(client, auth, project)
    first, second = ev["improvements"][:2]

    r = client.post(
        f"/projects/{project['id']}/improve",
        json={"decisions": [
            {"improvement_id": first["id"], "decision": "accepted"},
            {"improvement_id": second["id"], "decision": "edited",
             "edited_text": "Start with exam preparation only."},
        ]},
        headers=auth,
    )
    assert r.status_code == 202, r.text

    versions = client.get(f"/projects/{project['id']}/versions", headers=auth).json()
    assert [v["version_no"] for v in versions] == [2, 1] and versions[0]["is_current"]
    assert "commission" in client.get(f"/projects/{project['id']}", headers=auth).json()["version"]["idea_text"]

    v2 = client.get(f"/projects/{project['id']}/evaluations?version=2", headers=auth).json()[0]
    assert v2["baseline_evaluation_id"] == ev["id"]
    for dim in v2["dimensions"]:
        assert dim["previous_score"] == SCORES[dim["dimension"]]
        assert dim["score"] == SCORES[dim["dimension"]] + 8
        assert dim["change_reason"]

    r = client.get(f"/projects/{project['id']}/compare?a=1&b=2", headers=auth)
    assert r.status_code == 200, r.text
    cmp = r.json()
    assert cmp["overall_delta"] == v2["overall_score"] - ev["overall_score"]
    assert all(d["delta"] == 8 and d["reason"] for d in cmp["dimensions"])
    assert any(p["op"] == "added" for p in cmp["idea_diff"])
    assert cmp["change_summary"]

    decisions = db_session.scalars(select(ProjectFeedback.decision)).all()
    assert sorted(decisions) == ["accepted", "edited"]
    stored = client.get(f"/projects/{project['id']}/evaluations?version=1", headers=auth).json()[0]
    assert {i["decision"] for i in stored["improvements"][:2]} == {"accepted", "edited"}


def test_improve_validation(client, auth, project, fake_eval, db_session):
    r = client.post(f"/projects/{project['id']}/improve", json={"decisions": []}, headers=auth)
    assert r.status_code == 409  # nothing evaluated yet

    _with_evidence(client, auth, project)
    ev = _evaluate(client, auth, project)
    url = f"/projects/{project['id']}/improve"
    bad = client.post(url, json={"decisions": [{"improvement_id": "nope", "decision": "accepted"}]}, headers=auth)
    assert bad.status_code == 404
    edited = client.post(
        url, json={"decisions": [{"improvement_id": ev["improvements"][0]["id"], "decision": "edited"}]},
        headers=auth,
    )
    assert edited.status_code == 422
    rejected = client.post(
        url, json={"decisions": [{"improvement_id": ev["improvements"][0]["id"], "decision": "rejected"}]},
        headers=auth,
    )
    assert rejected.status_code == 422
    assert db_session.scalars(select(ProjectFeedback.decision)).all() == ["rejected"]

    # the user's own change alone is enough
    ok = client.post(url, json={"note": "Add a free tier for first-year students."}, headers=auth)
    assert ok.status_code == 202, ok.text


def test_compare_needs_evaluations_and_versions(client, auth, project, fake_eval):
    assert client.get(f"/projects/{project['id']}/compare?a=1&b=2", headers=auth).status_code == 404
    client.post(
        f"/projects/{project['id']}/versions",
        json={"idea_text": project["version"]["idea_text"] + " Now with group sessions."},
        headers=auth,
    )
    r = client.get(f"/projects/{project['id']}/compare?a=1&b=2", headers=auth)
    assert r.status_code == 409 and "no evaluation" in r.json()["detail"]


def test_evaluation_endpoints_are_owner_only(client, auth, project, fake_eval):
    other = register_and_login(client, "mallory@example.com")
    pid = project["id"]
    assert client.post(f"/projects/{pid}/evaluate", headers=other).status_code == 404
    assert client.get(f"/projects/{pid}/evaluations", headers=other).status_code == 404
    assert client.get(f"/projects/{pid}/compare?a=1&b=1", headers=other).status_code == 404
    assert client.post(f"/projects/{pid}/improve", json={"note": "x"}, headers=other).status_code == 404


def test_failed_evaluation_marks_run_failed(client, auth, project, fake_eval, monkeypatch, db_session):
    from app.services.evaluation import evaluator

    def boom(*a, **k):
        raise LLMError("model unavailable")

    monkeypatch.setattr(evaluator, "score_dimensions", boom)
    r = client.post(f"/projects/{project['id']}/evaluate", headers=auth)
    assert r.status_code == 502 and "Evaluation failed" in r.json()["detail"]
    run = db_session.scalar(select(AgentRun).where(AgentRun.agent_name == "evaluation"))
    db_session.refresh(run)
    assert run.status == "failed" and "model unavailable" in run.error_message
    assert client.get(f"/projects/{project['id']}/evaluations", headers=auth).json() == []
