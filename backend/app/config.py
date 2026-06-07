"""PR0-2 — Centralized, validated configuration.

All environment-driven config lives here so it's read once, typed, and checked at
startup instead of scattered ``os.environ`` calls.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Shipped default — fine for local dev, refused in production.
DEFAULT_AUTH_SECRET = "dev-secret-change-me-in-production-0123456789abcdef"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    env: str = "development"

    # Persistence
    database_url: str = "sqlite:///./localmv.db"
    storage_dir: str = "projects"

    # Auth
    auth_secret: str = DEFAULT_AUTH_SECRET

    # Web
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 100

    # Jobs: when true, generation endpoints enqueue and a separate worker runs
    # them; when false (default), they run inline in the request.
    async_jobs: bool = False

    # Per-user quotas
    max_projects_per_user: int = 50
    max_active_jobs_per_user: int = 50

    # Auth: short-lived access tokens + simple rate limiting on auth endpoints.
    access_token_minutes: int = 60
    rate_limit_window_seconds: int = 60
    rate_limit_max_attempts: int = 10

    # Model servers / external services
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    comfyui_host: str = "http://localhost:8188"
    acestep_model: str = "ace-step-v1"
    cloud_video_url: str = ""
    cloud_video_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def secret_is_secure(self) -> bool:
        return self.auth_secret not in ("", DEFAULT_AUTH_SECRET)


class ConfigurationError(RuntimeError):
    """Raised when configuration is unsafe for the target environment."""


def assert_production_ready(settings: "Settings") -> None:
    """Fail fast if running in production with insecure config."""
    if settings.is_production and not settings.secret_is_secure:
        raise ConfigurationError(
            "AUTH_SECRET must be set to a non-default value in production"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
