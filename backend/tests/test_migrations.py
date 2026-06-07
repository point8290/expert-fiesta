"""Tests for PR0-4 — Alembic migrations build the schema end to end."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_upgrade_head_creates_schema(tmp_path, monkeypatch):
    db_file = tmp_path / "migrated.db"
    url = f"sqlite:///{db_file}"
    # env.py reads the URL from settings; point it at the temp DB.
    monkeypatch.setenv("DATABASE_URL", url)
    from app.config import get_settings

    get_settings.cache_clear()

    command.upgrade(_alembic_config(url), "head")

    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"users", "projects", "scenes", "characters", "jobs"} <= tables

    get_settings.cache_clear()


def test_owner_id_is_not_null_after_migration(tmp_path, monkeypatch):
    db_file = tmp_path / "migrated2.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(_alembic_config(url), "head")

    cols = {
        c["name"]: c
        for c in inspect(create_engine(url)).get_columns("projects")
    }
    assert cols["owner_id"]["nullable"] is False

    get_settings.cache_clear()
