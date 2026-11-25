from __future__ import annotations

from tests.conftest import register_and_login


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_login_me(client):
    headers = register_and_login(client, "Carol@Example.com")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "carol@example.com"
    assert body["daily_token_limit"] == 200_000
    assert "password_hash" not in body


def test_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    again = client.post("/auth/register", json={**payload, "email": "DUP@example.com"})
    assert again.status_code == 409


def test_short_password_rejected(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422


def test_wrong_password_is_401(client):
    register_and_login(client, "dave@example.com")
    r = client.post("/auth/login", json={"email": "dave@example.com", "password": "nope-nope"})
    assert r.status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_login_is_rate_limited(client):
    payload = {"email": "nobody@example.com", "password": "whatever1"}
    codes = [client.post("/auth/login", json=payload).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_register_is_rate_limited(client):
    codes = [
        client.post(
            "/auth/register", json={"email": f"u{i}@example.com", "password": "password123"}
        ).status_code
        for i in range(11)
    ]
    assert codes[:10] == [201] * 10
    assert codes[10] == 429
