from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.agent import AgentRun
from app.models.user import User
from app.schemas.nlp import RequirementItem
from app.services.llm.base import LLMError
from tests.conftest import IDEA, TOKENS


def test_create_list_read_update_delete(client, auth, project):
    assert project["status"] == "draft"
    assert project["version"]["version_no"] == 1
    assert project["version"]["idea_text"] == IDEA
    assert project["requirements"] == []

    listed = client.get("/projects", headers=auth).json()
    assert [p["id"] for p in listed] == [project["id"]]

    pid = project["id"]
    r = client.patch(f"/projects/{pid}", json={"title": "Tutor finder v2"}, headers=auth)
    assert r.status_code == 200 and r.json()["title"] == "Tutor finder v2"

    assert client.delete(f"/projects/{pid}", headers=auth).status_code == 204
    assert client.get(f"/projects/{pid}", headers=auth).status_code == 404


def test_validation_rejects_short_idea(client, auth):
    r = client.post("/projects", json={"title": "abc", "idea_text": "too short"}, headers=auth)
    assert r.status_code == 422


def test_other_users_get_404(client, auth, other_auth, project, fake_llm):
    pid = project["id"]
    run_id = client.post(f"/projects/{pid}/understand", headers=auth).json()["run_id"]

    for method, path in [
        ("get", f"/projects/{pid}"),
        ("patch", f"/projects/{pid}"),
        ("delete", f"/projects/{pid}"),
        ("get", f"/projects/{pid}/requirements"),
        ("post", f"/projects/{pid}/understand"),
        ("post", f"/projects/{pid}/requirements/regenerate"),
        ("get", f"/projects/{pid}/versions"),
        ("get", f"/projects/{pid}/versions/1"),
        ("post", f"/projects/{pid}/versions/1/restore"),
        ("get", f"/runs/{run_id}"),
    ]:
        kwargs = {"json": {"title": "stolen"}} if method == "patch" else {}
        r = getattr(client, method)(path, headers=other_auth, **kwargs)
        assert r.status_code == 404, (method, path, r.status_code)

    assert client.get("/projects", headers=other_auth).json() == []
    # the owner still sees it untouched
    assert client.get(f"/projects/{pid}", headers=auth).json()["title"] == "Tutor finder"


def test_understand_extracts_structure_and_requirements(client, auth, project, fake_llm):
    pid = project["id"]
    r = client.post(f"/projects/{pid}/understand", headers=auth)
    assert r.status_code == 202
    assert r.json()["status"] == "succeeded"

    run = client.get(f"/runs/{r.json()['run_id']}", headers=auth).json()
    assert run["status"] == "succeeded"
    assert run["tokens_in"] + run["tokens_out"] == 3 * TOKENS

    detail = client.get(f"/projects/{pid}", headers=auth).json()
    assert detail["status"] == "ready"
    assert detail["category"] == "business"
    assert detail["version"]["structured_idea"]["problem"]
    assert len(detail["requirements"]) == 3


def test_pipeline_failure_marks_run_and_project_failed(
    client, auth, project, fake_llm, db_session
):
    fake_llm.fail_with = LLMError("model returned garbage")
    pid = project["id"]
    r = client.post(f"/projects/{pid}/understand", headers=auth)
    assert r.status_code == 502
    assert "garbage" in r.json()["detail"]

    detail = client.get(f"/projects/{pid}", headers=auth).json()
    assert detail["status"] == "failed"
    assert detail["requirements"] == []

    run = db_session.scalar(select(AgentRun))
    assert run.status == "failed"
    assert "garbage" in run.error_message
    assert run.finished_at is not None


def test_requirement_patch_is_atomic(client, auth, project, fake_llm):
    pid = project["id"]
    client.post(f"/projects/{pid}/understand", headers=auth)
    reqs = client.get(f"/projects/{pid}/requirements", headers=auth).json()

    bad = client.patch(
        f"/projects/{pid}/requirements",
        json={
            "requirements": [
                {"id": reqs[0]["id"], "confirmed": True},
                {"id": str(uuid.uuid4()), "confirmed": True},
            ]
        },
        headers=auth,
    )
    assert bad.status_code == 404
    after = client.get(f"/projects/{pid}/requirements", headers=auth).json()
    assert not any(r["confirmed"] for r in after), "a partial update leaked through"

    good = client.patch(
        f"/projects/{pid}/requirements",
        json={"requirements": [{"id": reqs[0]["id"], "confirmed": True, "priority": "could"}]},
        headers=auth,
    )
    assert good.status_code == 200
    row = next(r for r in good.json() if r["id"] == reqs[0]["id"])
    assert row["confirmed"] is True and row["priority"] == "could" and row["source"] == "user"


def test_regenerate_keeps_confirmed_and_user_rows(client, auth, project, fake_llm):
    pid = project["id"]
    client.post(f"/projects/{pid}/understand", headers=auth)
    reqs = client.get(f"/projects/{pid}/requirements", headers=auth).json()
    kept = reqs[0]
    client.patch(
        f"/projects/{pid}/requirements",
        json={"requirements": [{"id": kept["id"], "confirmed": True}]},
        headers=auth,
    )

    fake_llm.requirements = [
        RequirementItem(
            req_type="functional", description="Tutors can set availability", priority="must"
        ),
        # same text as the kept row: must not be duplicated
        RequirementItem(req_type="functional", description=kept["description"], priority="must"),
    ]
    r = client.post(f"/projects/{pid}/requirements/regenerate", headers=auth)
    assert r.status_code == 202, r.text

    after = client.get(f"/projects/{pid}/requirements", headers=auth).json()
    assert sorted(x["description"] for x in after) == sorted(
        [kept["description"], "Tutors can set availability"]
    )
    assert any(x["id"] == kept["id"] and x["confirmed"] for x in after)


def test_daily_token_limit_is_enforced(client, auth, project, fake_llm, db_session):
    user = db_session.scalar(select(User))
    user.daily_token_limit = 3 * TOKENS  # exactly one understanding run
    db_session.commit()

    pid = project["id"]
    assert client.post(f"/projects/{pid}/understand", headers=auth).status_code == 202
    blocked = client.post(f"/projects/{pid}/understand", headers=auth)
    assert blocked.status_code == 429
    assert "Daily AI token limit" in blocked.json()["detail"]
    regen = client.post(f"/projects/{pid}/requirements/regenerate", headers=auth)
    assert regen.status_code == 429


def test_understand_without_llm_key_fails_cleanly(client, auth, project, monkeypatch):
    import app.services.nlp.extraction as extraction
    from app.config import Settings
    from app.services.llm.groq import GroqProvider

    # no fake LLM here: the real provider, configured without a key
    monkeypatch.setattr(
        extraction, "get_llm", lambda: GroqProvider(Settings(groq_api_key=None))
    )

    r = client.post(f"/projects/{project['id']}/understand", headers=auth)
    assert r.status_code == 502
    assert "GROQ_API_KEY" in r.json()["detail"]


def test_failed_regeneration_keeps_project_ready(client, auth, project, fake_llm):
    pid = project["id"]
    client.post(f"/projects/{pid}/understand", headers=auth)
    fake_llm.fail_with = LLMError("rate limited")
    r = client.post(f"/projects/{pid}/requirements/regenerate", headers=auth)
    assert r.status_code == 502
    detail = client.get(f"/projects/{pid}", headers=auth).json()
    assert detail["status"] == "ready"
    assert len(detail["requirements"]) == 3
