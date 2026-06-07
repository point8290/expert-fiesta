"""Tests for P5-S2 — Multi-user authentication + per-user project isolation."""


def _register(anon_client, email, password="secret123"):
    res = anon_client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert res.status_code == 201
    return res.json()["accessToken"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_a_token(anon_client):
    res = anon_client.post(
        "/auth/register", json={"email": "a@example.com", "password": "secret123"}
    )
    assert res.status_code == 201
    body = res.json()
    assert body["accessToken"]
    assert body["tokenType"] == "bearer"


def test_register_duplicate_email_returns_400(anon_client):
    anon_client.post("/auth/register", json={"email": "dup@x.com", "password": "secret123"})
    res = anon_client.post(
        "/auth/register", json={"email": "dup@x.com", "password": "secret123"}
    )
    assert res.status_code == 400


def test_login_with_valid_and_invalid_credentials(anon_client):
    anon_client.post("/auth/register", json={"email": "l@x.com", "password": "secret123"})

    ok = anon_client.post("/auth/login", json={"email": "l@x.com", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["accessToken"]

    bad = anon_client.post("/auth/login", json={"email": "l@x.com", "password": "wrong0"})
    assert bad.status_code == 401

    missing = anon_client.post(
        "/auth/login", json={"email": "nobody@x.com", "password": "secret123"}
    )
    assert missing.status_code == 401


def test_me_returns_current_user(anon_client):
    token = _register(anon_client, "me@example.com")
    res = anon_client.get("/auth/me", headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["email"] == "me@example.com"


def test_protected_endpoint_requires_auth(anon_client, project_payload):
    # No token -> 401.
    assert anon_client.post("/projects", json=project_payload).status_code == 401
    # Garbage token -> 401.
    res = anon_client.post(
        "/projects", json=project_payload, headers=_auth("not-a-real-token")
    )
    assert res.status_code == 401


def test_projects_are_isolated_per_user(anon_client, project_payload):
    token_a = _register(anon_client, "alice@example.com")
    token_b = _register(anon_client, "bob@example.com")

    created = anon_client.post(
        "/projects", json=project_payload, headers=_auth(token_a)
    ).json()
    pid = created["id"]

    # Bob cannot see or fetch Alice's project.
    bob_list = anon_client.get("/projects", headers=_auth(token_b)).json()
    assert all(p["id"] != pid for p in bob_list)
    assert anon_client.get(f"/projects/{pid}", headers=_auth(token_b)).status_code == 404
    assert (
        anon_client.patch(
            f"/projects/{pid}", json={"mood": "x"}, headers=_auth(token_b)
        ).status_code
        == 404
    )

    # Alice can.
    assert anon_client.get(f"/projects/{pid}", headers=_auth(token_a)).status_code == 200
    alice_list = anon_client.get("/projects", headers=_auth(token_a)).json()
    assert any(p["id"] == pid for p in alice_list)
