"""Tests for CB-5 — GPU-second metering + budget caps."""
import time

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.models import Job, Project
from app.services.jobs import create_job, run_job
from app.services.quota import assert_gpu_budget


def _project(db_session, payload, owner_id):
    p = Project(
        owner_id=owner_id, title=payload["title"], idea=payload["idea"],
        genre=payload["genre"], mood=payload["mood"], visual_style=payload["visualStyle"],
        target_duration=payload["targetDuration"], aspect_ratio=payload["aspectRatio"],
    )
    db_session.add(p)
    db_session.commit()
    return p


def test_run_job_records_gpu_seconds(db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    job = create_job(db_session, "clip", project.id)
    db_session.commit()

    run_job(db_session, job, lambda progress: (time.sleep(0.02), "/out.mp4")[1])
    assert job.gpu_seconds >= 0.02


def test_usage_includes_gpu_seconds(client, db_session, project_payload, default_user):
    project = client.post("/projects", json=project_payload).json()
    db_session.add(Job(project_id=project["id"], type="clip", status="succeeded", gpu_seconds=12.5))
    db_session.commit()

    usage = client.get(f"/projects/{project['id']}/usage").json()
    assert usage["totalGpuSeconds"] == 12.5


def test_gpu_budget_enforced(db_session, project_payload, default_user, monkeypatch):
    project = _project(db_session, project_payload, default_user.id)
    db_session.add(Job(project_id=project.id, type="clip", status="succeeded", gpu_seconds=100.0))
    db_session.commit()

    monkeypatch.setenv("MAX_GPU_SECONDS_PER_USER", "50")
    get_settings.cache_clear()
    try:
        with pytest.raises(HTTPException) as exc:
            assert_gpu_budget(db_session, default_user)
        assert exc.value.status_code == 429
    finally:
        get_settings.cache_clear()


def test_gpu_budget_unlimited_by_default(db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    db_session.add(Job(project_id=project.id, type="clip", status="succeeded", gpu_seconds=1e6))
    db_session.commit()
    assert_gpu_budget(db_session, default_user)  # no cap configured -> no raise
