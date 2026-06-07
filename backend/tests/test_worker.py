"""Tests for PR0-5 — background job worker (claim + run handlers)."""
from app.models import Project
from app.services.jobs import create_job
from app.worker import claim_next_job, process_one


def _project(db_session, payload, owner_id):
    project = Project(
        owner_id=owner_id,
        title=payload["title"], idea=payload["idea"], genre=payload["genre"],
        mood=payload["mood"], visual_style=payload["visualStyle"],
        target_duration=payload["targetDuration"], aspect_ratio=payload["aspectRatio"],
    )
    db_session.add(project)
    db_session.commit()
    return project


def test_claim_returns_oldest_queued(db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    first = create_job(db_session, "clip", project.id)
    create_job(db_session, "clip", project.id)
    db_session.commit()
    assert claim_next_job(db_session).id == first.id


def test_process_one_runs_handler_and_succeeds(db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    job = create_job(db_session, "demo", project.id)
    db_session.commit()

    seen = []

    def handler(db, j, progress):
        progress(0.5)
        seen.append(j.id)
        return "/out/clip.mp4"

    ran = process_one(db_session, handlers={"demo": handler})
    assert ran is True
    assert seen == [job.id]
    assert job.status == "succeeded"
    assert job.progress == 1.0
    assert job.result_path == "/out/clip.mp4"


def test_process_one_marks_failed_on_handler_error(db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    job = create_job(db_session, "demo", project.id)
    db_session.commit()

    def boom(db, j, progress):
        raise RuntimeError("gpu melted")

    process_one(db_session, handlers={"demo": boom})
    assert job.status == "failed"
    assert "gpu melted" in job.error


def test_process_one_no_handler_marks_failed(db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    job = create_job(db_session, "mystery", project.id)
    db_session.commit()
    process_one(db_session, handlers={})
    assert job.status == "failed"
    assert "No handler" in job.error


def test_process_one_empty_queue_returns_false(db_session):
    assert process_one(db_session, handlers={}) is False
