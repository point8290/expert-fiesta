"""Database setup: SQLite engine, session factory, and the FastAPI dependency.

Local-first: a single SQLite file is all one creator needs. Tests override
``get_db`` with an in-memory database (see ``tests/conftest.py``).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

DATABASE_URL = get_settings().database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
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
