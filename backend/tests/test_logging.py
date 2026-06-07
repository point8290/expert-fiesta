"""Tests for PR1-2 — request-id propagation (structured logging support)."""


def test_response_carries_a_request_id(client):
    res = client.get("/health")
    assert res.headers.get("x-request-id")


def test_incoming_request_id_is_echoed(client):
    res = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert res.headers.get("x-request-id") == "trace-123"
