import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import User
from app.services.auth import hash_password

DEFAULT_EMAIL = "default@example.com"
# Hash once for the whole session; bcrypt is deliberately slow per call.
_DEFAULT_HASH = hash_password("password")


@pytest.fixture()
def db_engine():
    """A throwaway in-memory SQLite engine shared by the client and db_session."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    # Seed a default user so authenticated tests have an owner out of the box.
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(User(email=DEFAULT_EMAIL, hashed_password=_DEFAULT_HASH))
    session.commit()
    session.close()
    return engine


@pytest.fixture()
def default_user(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    user = session.scalar(select(User).where(User.email == DEFAULT_EMAIL))
    session.close()
    return user


@pytest.fixture()
def client(db_engine):
    """A TestClient authenticated as the default user (auth dependency overridden)."""
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_current_user(db: Session = Depends(get_db)) -> User:
        return db.scalar(select(User).where(User.email == DEFAULT_EMAIL))

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client(db_engine):
    """A TestClient with NO auth override — requests must carry a real token."""
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
