"""Tests for P1-S1 — Create and manage projects."""


def test_create_project_returns_created_resource(client, project_payload):
    # AC1: valid body creates a project with id, status, timestamps.
    res = client.post("/projects", json=project_payload)
    assert res.status_code == 201
    body = res.json()
    assert body["id"]
    assert body["title"] == project_payload["title"]
    assert body["status"] == "draft"
    assert body["createdAt"]
    assert body["updatedAt"]


def test_create_project_validates_required_fields(client, project_payload):
    # AC2 / AC7: missing required field -> 422.
    incomplete = dict(project_payload)
    del incomplete["title"]
    res = client.post("/projects", json=incomplete)
    assert res.status_code == 422


def test_list_projects_returns_newest_first(client, project_payload):
    # AC3: list returns all projects, newest first.
    first = client.post("/projects", json={**project_payload, "title": "First"}).json()
    second = client.post("/projects", json={**project_payload, "title": "Second"}).json()

    res = client.get("/projects")
    assert res.status_code == 200
    titles = [p["title"] for p in res.json()]
    assert titles.index("Second") < titles.index("First")
    ids = [p["id"] for p in res.json()]
    assert first["id"] in ids and second["id"] in ids


def test_get_project_by_id(client, project_payload):
    # AC4: get returns the project; unknown id -> 404.
    created = client.post("/projects", json=project_payload).json()
    res = client.get(f"/projects/{created['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]

    missing = client.get("/projects/does-not-exist")
    assert missing.status_code == 404


def test_update_project_bumps_updated_at(client, project_payload):
    # AC5: patch updates editable fields and bumps updatedAt.
    created = client.post("/projects", json=project_payload).json()
    res = client.patch(
        f"/projects/{created['id']}",
        json={"mood": "hopeful", "targetDuration": 45},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["mood"] == "hopeful"
    assert body["targetDuration"] == 45
    assert body["updatedAt"] >= created["updatedAt"]


def test_update_unknown_project_returns_404(client):
    res = client.patch("/projects/nope", json={"mood": "calm"})
    assert res.status_code == 404


def test_delete_project(client, project_payload):
    # AC6: delete removes the project.
    created = client.post("/projects", json=project_payload).json()
    res = client.delete(f"/projects/{created['id']}")
    assert res.status_code == 204
    assert client.get(f"/projects/{created['id']}").status_code == 404


def test_delete_unknown_project_returns_404(client):
    assert client.delete("/projects/nope").status_code == 404
