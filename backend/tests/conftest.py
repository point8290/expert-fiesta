import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_engine():
    """A throwaway in-memory SQLite engine shared by the client and db_session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def client(db_engine):
    """A TestClient backed by the shared in-memory database."""
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(db_engine):
    """A session bound to the same engine as ``client`` for direct DB access."""
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def project_payload():
    return {
        "title": "Wings We Leave Behind",
        "idea": "A story about childhood friends, memories, and birds",
        "genre": "cinematic pop rock",
        "mood": "bittersweet and uplifting",
        "visualStyle": "2D hand-painted animation",
        "targetDuration": 60,
        "aspectRatio": "16:9",
    }
