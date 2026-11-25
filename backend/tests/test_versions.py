from __future__ import annotations

NEW_IDEA = (
    "An AI platform that matches university students with affordable peer tutors "
    "and group sessions, paid per session."
)


def test_create_list_read_restore(client, auth, project, fake_llm):
    pid = project["id"]
    client.post(f"/projects/{pid}/understand", headers=auth)

    r = client.post(
        f"/projects/{pid}/versions",
        json={"idea_text": NEW_IDEA, "change_summary": "Peer tutors and group sessions"},
        headers=auth,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["version"]["version_no"] == 2
    assert body["version"]["idea_text"] == NEW_IDEA
    assert body["requirements"] == []  # not copied by default
    assert body["status"] == "draft"
    assert body["current_version_id"] == body["version"]["id"]

    versions = client.get(f"/projects/{pid}/versions", headers=auth).json()
    assert [v["version_no"] for v in versions] == [2, 1]
    assert versions[0]["is_current"] and not versions[1]["is_current"]
    assert versions[1]["has_structure"] and not versions[0]["has_structure"]
    assert versions[0]["parent_version_id"] == versions[1]["id"]

    v1 = client.get(f"/projects/{pid}/versions/1", headers=auth).json()
    assert len(v1["requirements"]) == 3 and v1["is_current"] is False

    # understanding now targets version 2 and leaves version 1 alone
    client.post(f"/projects/{pid}/understand", headers=auth)
    v2 = client.get(f"/projects/{pid}/versions/2", headers=auth).json()
    assert len(v2["requirements"]) == 3 and v2["structured_idea"]
    assert len(client.get(f"/projects/{pid}/versions/1", headers=auth).json()["requirements"]) == 3

    restored = client.post(f"/projects/{pid}/versions/1/restore", headers=auth).json()
    assert restored["version"]["version_no"] == 1
    assert restored["status"] == "ready"
    assert client.get(f"/projects/{pid}", headers=auth).json()["version"]["version_no"] == 1


def test_copy_requirements(client, auth, project, fake_llm):
    pid = project["id"]
    client.post(f"/projects/{pid}/understand", headers=auth)
    r = client.post(
        f"/projects/{pid}/versions",
        json={"idea_text": NEW_IDEA, "copy_requirements": True},
        headers=auth,
    ).json()
    assert len(r["requirements"]) == 3
    assert not any(req["confirmed"] for req in r["requirements"])


def test_unknown_version_is_404(client, auth, project):
    pid = project["id"]
    assert client.get(f"/projects/{pid}/versions/9", headers=auth).status_code == 404
    assert client.post(f"/projects/{pid}/versions/9/restore", headers=auth).status_code == 404


def test_new_version_validates_text(client, auth, project):
    r = client.post(
        f"/projects/{project['id']}/versions", json={"idea_text": "short"}, headers=auth
    )
    assert r.status_code == 422
