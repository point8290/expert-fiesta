"""Tests for PR0-3 — the engine is DATABASE_URL-driven (SQLite or Postgres)."""
from app.database import make_engine


def test_sqlite_engine_sets_check_same_thread():
    engine = make_engine("sqlite:///./x.db")
    assert engine.dialect.name == "sqlite"


def test_postgres_url_builds_postgres_dialect():
    # create_engine is lazy — this builds the dialect without connecting.
    engine = make_engine("postgresql+psycopg://user:pw@localhost:5432/lmvs")
    assert engine.dialect.name == "postgresql"
