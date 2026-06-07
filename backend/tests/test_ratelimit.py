"""Tests for PR1-1 AC1 — rate limiting on auth endpoints."""
from app.config import get_settings
from app.ratelimit import _attempts


def test_login_is_rate_limited(anon_client, monkeypatch):
    _attempts.clear()
    monkeypatch.setenv("RATE_LIMIT_MAX_ATTEMPTS", "2")
    get_settings.cache_clear()
    try:
        creds = {"email": "x@example.com", "password": "secret123"}
        assert anon_client.post("/auth/login", json=creds).status_code == 401
        assert anon_client.post("/auth/login", json=creds).status_code == 401
        # Third attempt within the window is blocked.
        assert anon_client.post("/auth/login", json=creds).status_code == 429
    finally:
        _attempts.clear()
        get_settings.cache_clear()


def test_register_is_rate_limited(anon_client, monkeypatch):
    _attempts.clear()
    monkeypatch.setenv("RATE_LIMIT_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()
    try:
        first = anon_client.post(
            "/auth/register", json={"email": "a@b.com", "password": "secret123"}
        )
        assert first.status_code == 201
        second = anon_client.post(
            "/auth/register", json={"email": "c@d.com", "password": "secret123"}
        )
        assert second.status_code == 429
    finally:
        _attempts.clear()
        get_settings.cache_clear()
