"""Tests for PR1-6 — pagination on list endpoints."""
import pytest


@pytest.fixture()
def three_projects(client, project_payload):
    return [
        client.post("/projects", json={**project_payload, "title": f"P{i}"}).json()
        for i in range(3)
    ]


def test_limit_caps_results(client, three_projects):
    res = client.get("/projects?limit=2")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_offset_skips_results(client, three_projects):
    page1 = client.get("/projects?limit=2&offset=0").json()
    page2 = client.get("/projects?limit=2&offset=2").json()
    assert len(page1) == 2
    assert len(page2) == 1
    ids = {p["id"] for p in page1} | {p["id"] for p in page2}
    assert len(ids) == 3  # no overlap across pages


def test_limit_over_cap_is_rejected(client):
    assert client.get("/projects?limit=1000").status_code == 422


def test_default_returns_all_when_few(client, three_projects):
    assert len(client.get("/projects").json()) == 3
