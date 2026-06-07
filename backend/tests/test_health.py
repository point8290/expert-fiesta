"""Tests for PR1-4 — liveness (/health) vs readiness (/ready)."""


def test_health_is_liveness_only(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ready_checks_database(client):
    res = client.get("/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
