"""Tests for CORS (PR0 — lets the browser frontend call the API cross-origin)."""


def test_cors_allows_configured_origin(client):
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_preflight_on_projects(client):
    res = client.options(
        "/projects",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_omits_unknown_origin(client):
    res = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert res.headers.get("access-control-allow-origin") != "http://evil.example.com"
