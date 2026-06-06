import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    """A TestClient backed by a throwaway in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

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
