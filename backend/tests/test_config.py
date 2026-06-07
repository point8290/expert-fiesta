"""Tests for PR0-2 — centralized config + production secret validation."""
import pytest

from app.config import (
    DEFAULT_AUTH_SECRET,
    ConfigurationError,
    Settings,
    assert_production_ready,
)


def test_defaults():
    s = Settings()
    assert s.database_url.startswith("sqlite")
    assert s.cors_origin_list == ["http://localhost:3000"]
    assert s.is_production is False


def test_cors_origins_parses_comma_separated():
    s = Settings(cors_origins="https://a.com, https://b.com")
    assert s.cors_origin_list == ["https://a.com", "https://b.com"]


def test_production_with_default_secret_is_rejected():
    s = Settings(env="production", auth_secret=DEFAULT_AUTH_SECRET)
    with pytest.raises(ConfigurationError):
        assert_production_ready(s)


def test_production_with_custom_secret_is_ok():
    s = Settings(env="production", auth_secret="a-real-long-random-production-secret")
    assert_production_ready(s)  # no raise
    assert s.is_production is True
    assert s.secret_is_secure is True


def test_development_with_default_secret_is_ok():
    s = Settings(env="development", auth_secret=DEFAULT_AUTH_SECRET)
    assert_production_ready(s)  # dev is allowed to use the default
