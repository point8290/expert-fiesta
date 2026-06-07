"""Tests for PR1-5 — per-user quotas (429 over limit)."""
import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.models import Job, Project
from app.services.quota import assert_active_job_quota


def test_project_quota_enforced(client, project_payload, monkeypatch):
    monkeypatch.setenv("MAX_PROJECTS_PER_USER", "1")
    get_settings.cache_clear()
    try:
        first = client.post("/projects", json=project_payload)
        assert first.status_code == 201
        second = client.post("/projects", json=project_payload)
        assert second.status_code == 429
    finally:
        get_settings.cache_clear()


def test_active_job_quota_raises_at_cap(db_session, project_payload, default_user, monkeypatch):
    project = Project(
        owner_id=default_user.id, title="t", idea="i", genre="g", mood="m",
        visual_style="v", target_duration=40, aspect_ratio="16:9",
    )
    db_session.add(project)
    db_session.commit()
    db_session.add_all(
        [Job(project_id=project.id, type="clip", status="queued") for _ in range(2)]
    )
    db_session.commit()

    monkeypatch.setenv("MAX_ACTIVE_JOBS_PER_USER", "2")
    get_settings.cache_clear()
    try:
        with pytest.raises(HTTPException) as exc:
            assert_active_job_quota(db_session, default_user)
        assert exc.value.status_code == 429
    finally:
        get_settings.cache_clear()
