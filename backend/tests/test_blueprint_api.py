"""Phase 4 through the API: generate, list, regenerate one section, edit, history (DB tests).

The LLM is a schema-aware fake (``tests/blueprint_fakes.py``); understanding uses the
shared fake from ``conftest``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.agent import AgentRun, ProjectArtifact
from tests.blueprint_fakes import FakeBlueprintProvider
from tests.conftest import register_and_login

TYPES = ["ui_ux", "architecture", "database_schema", "api_spec", "prd", "roadmap"]


@pytest.fixture
def fake_blueprint(monkeypatch, fake_llm):
    from app.services.blueprint import agent

    provider = FakeBlueprintProvider()
    monkeypatch.setattr(agent, "get_llm", lambda: provider)
    return provider


def _generate(client, auth, project):
    r = client.post(f"/projects/{project['id']}/blueprint", headers=auth)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "succeeded"
    r = client.get(f"/projects/{project['id']}/artifacts", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def test_one_idea_produces_a_complete_blueprint(client, auth, project, fake_blueprint, db_session):
    before = client.get(f"/projects/{project['id']}/artifacts", headers=auth).json()
    assert before["artifacts"] == [] and before["missing"] == TYPES and before["has_evaluation"] is False

    bp = _generate(client, auth, project)
    assert bp["missing"] == [] and bp["version_no"] == 1
    assert [a["artifact_type"] for a in bp["artifacts"]] == TYPES
    for a in bp["artifacts"]:
        assert a["artifact_version"] == 1 and a["edited_by_user"] is False and a["format"] == "markdown"
        assert a["content"].startswith("# ") and a["stale_inputs"] == []
        assert a["data"]["prompt_version"] == "blueprint/v1" and "result" in a["data"]
    by_type = {a["artifact_type"]: a for a in bp["artifacts"]}
    assert "```mermaid\nflowchart LR" in by_type["architecture"]["content"]
    assert "```mermaid\nerDiagram" in by_type["database_schema"]["content"]
    assert by_type["roadmap"]["data"]["based_on"] == {t: 1 for t in TYPES[:-1]}
    assert any("not been evaluated" in n for n in by_type["prd"]["data"]["notices"])
    assert any("KB-B" in n for n in by_type["architecture"]["data"]["notices"])
    assert by_type["roadmap"]["data"]["notices"] == []  # notices only where they apply

    run = db_session.scalar(select(AgentRun).where(AgentRun.agent_name == "blueprint"))
    assert run.status == "succeeded" and run.prompt_version == "blueprint/v1" and run.tokens_in > 0
    assert run.output_ref["sections"] == {t: 1 for t in TYPES}
    # the project had no structure yet, so understanding ran first on its own run
    assert db_session.scalar(select(AgentRun).where(AgentRun.agent_name == "understanding"))
    assert fake_blueprint.calls.count("ProductDesignResult") == 1


def test_regenerating_one_section_leaves_the_rest_alone(client, auth, project, fake_blueprint, db_session):
    bp = _generate(client, auth, project)
    ids_before = {a["artifact_type"]: a["id"] for a in bp["artifacts"]}
    fake_blueprint.calls.clear()

    r = client.post(
        f"/projects/{project['id']}/artifacts/database_schema/regenerate",
        json={"instructions": "Use soft deletes everywhere."},
        headers=auth,
    )
    assert r.status_code == 202, r.text
    assert fake_blueprint.calls == ["SchemaResult"]  # nothing else was redone
    assert "Use soft deletes everywhere." in fake_blueprint.prompts["SchemaResult"]

    after = {a["artifact_type"]: a for a in client.get(f"/projects/{project['id']}/artifacts", headers=auth).json()["artifacts"]}
    assert after["database_schema"]["artifact_version"] == 2
    assert after["database_schema"]["instructions"] == "Use soft deletes everywhere."
    for t in TYPES:
        if t != "database_schema":
            assert after[t]["id"] == ids_before[t] and after[t]["artifact_version"] == 1
    # sections built on the old schema are now marked stale
    assert after["api_spec"]["stale_inputs"] == ["database_schema"]
    assert after["roadmap"]["stale_inputs"] == ["database_schema"]
    assert after["prd"]["stale_inputs"] == []

    history = client.get(f"/projects/{project['id']}/artifacts/database_schema/history", headers=auth).json()
    assert [h["artifact_version"] for h in history] == [2, 1]
    assert db_session.query(ProjectArtifact).count() == 7


def test_user_edit_creates_a_new_version(client, auth, project, fake_blueprint):
    bp = _generate(client, auth, project)
    prd = next(a for a in bp["artifacts"] if a["artifact_type"] == "prd")

    r = client.patch(f"/artifacts/{prd['id']}", json={"content": prd["content"] + "\n## Notes\n\nPilot at one campus.\n"}, headers=auth)
    assert r.status_code == 201, r.text
    edited = r.json()
    assert edited["artifact_version"] == 2 and edited["edited_by_user"] is True and edited["id"] != prd["id"]
    assert "Pilot at one campus." in edited["content"]

    assert client.get(f"/artifacts/{prd['id']}", headers=auth).json()["content"] == prd["content"]  # v1 kept
    latest = client.get(f"/projects/{project['id']}/artifacts", headers=auth).json()
    by_type = {a["artifact_type"]: a for a in latest["artifacts"]}
    assert by_type["prd"]["id"] == edited["id"]
    assert by_type["roadmap"]["stale_inputs"] == ["prd"]

    same = client.patch(f"/artifacts/{edited['id']}", json={"content": edited["content"]}, headers=auth)
    assert same.status_code == 422

    # the roadmap regenerated after the edit sees the user's text
    client.post(f"/projects/{project['id']}/artifacts/roadmap/regenerate", json={}, headers=auth)
    assert "PRD (edited by the user)" in fake_blueprint.prompts["RoadmapResult"]
    assert "Pilot at one campus." in fake_blueprint.prompts["RoadmapResult"]


def test_validation_and_ownership(client, auth, project, fake_blueprint):
    pid = project["id"]
    assert client.post(f"/projects/{pid}/artifacts/business_plan/regenerate", json={}, headers=auth).status_code == 422
    assert client.post(f"/projects/{pid}/artifacts/prd/regenerate", json={"instructions": "x" * 2001},
                       headers=auth).status_code == 422
    bp = _generate(client, auth, project)
    artifact_id = bp["artifacts"][0]["id"]

    other = register_and_login(client, "mallory@example.com")
    assert client.post(f"/projects/{pid}/blueprint", headers=other).status_code == 404
    assert client.get(f"/projects/{pid}/artifacts", headers=other).status_code == 404
    assert client.post(f"/projects/{pid}/artifacts/prd/regenerate", json={}, headers=other).status_code == 404
    assert client.get(f"/artifacts/{artifact_id}", headers=other).status_code == 404
    assert client.patch(f"/artifacts/{artifact_id}", json={"content": "mine now"}, headers=other).status_code == 404
    assert client.get(f"/projects/{pid}/artifacts?version=9", headers=auth).status_code == 404


def test_failed_section_marks_run_failed_and_keeps_finished_ones(client, auth, project, monkeypatch, fake_llm, db_session):
    from app.services.blueprint import agent

    provider = FakeBlueprintProvider(fail_on="ApiResult")
    monkeypatch.setattr(agent, "get_llm", lambda: provider)
    r = client.post(f"/projects/{project['id']}/blueprint", headers=auth)
    assert r.status_code == 502 and "Blueprint failed" in r.json()["detail"]

    run = db_session.scalar(select(AgentRun).where(AgentRun.agent_name == "blueprint"))
    db_session.refresh(run)
    assert run.status == "failed" and "model unavailable" in run.error_message
    bp = client.get(f"/projects/{project['id']}/artifacts", headers=auth).json()
    assert [a["artifact_type"] for a in bp["artifacts"]] == ["ui_ux", "architecture", "database_schema"]
    assert bp["missing"] == ["api_spec", "prd", "roadmap"]
