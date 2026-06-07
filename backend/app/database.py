"""Database setup: SQLite engine, session factory, and the FastAPI dependency.

Local-first: a single SQLite file is all one creator needs. Tests override
``get_db`` with an in-memory database (see ``tests/conftest.py``).
"""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


def make_engine(url: str) -> Engine:
    """Build an engine for any DATABASE_URL (SQLite needs check_same_thread)."""
    connect_args = (
        {"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


DATABASE_URL = get_settings().database_url
engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Yield a database session, closing it when the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
