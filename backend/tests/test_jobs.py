"""Tests for P2-S6 — Async jobs + progress."""
from app.models import Project
from app.services.jobs import create_job, run_job


def _project(db_session, payload):
    project = Project(
        title=payload["title"],
        idea=payload["idea"],
        genre=payload["genre"],
        mood=payload["mood"],
        visual_style=payload["visualStyle"],
        target_duration=payload["targetDuration"],
        aspect_ratio=payload["aspectRatio"],
    )
    db_session.add(project)
    db_session.commit()
    return project


def test_create_job_starts_queued(db_session, project_payload):
    project = _project(db_session, project_payload)
    job = create_job(db_session, "keyframe", project.id)
    assert job.status == "queued"
    assert job.progress == 0.0


def test_run_job_success_records_progress_and_result(db_session, project_payload):
    project = _project(db_session, project_payload)
    job = create_job(db_session, "keyframe", project.id)

    seen: list[float] = []

    def task(progress):
        progress(0.5)
        seen.append(0.5)
        return "/path/to/keyframe.png"

    run_job(db_session, job, task)
    assert job.status == "succeeded"
    assert job.progress == 1.0
    assert job.result_path == "/path/to/keyframe.png"
    assert seen == [0.5]


def test_run_job_failure_captures_error(db_session, project_payload):
    project = _project(db_session, project_payload)
    job = create_job(db_session, "keyframe", project.id)

    def task(progress):
        raise RuntimeError("comfyui exploded")

    run_job(db_session, job, task)
    assert job.status == "failed"
    assert "comfyui exploded" in job.error


def test_get_job_via_api(client, db_session, project_payload):
    project = client.post("/projects", json=project_payload).json()
    job = create_job(db_session, "render", project["id"])
    db_session.commit()

    res = client.get(f"/jobs/{job.id}")
    assert res.status_code == 200
    assert res.json()["type"] == "render"
    assert res.json()["status"] == "queued"


def test_list_project_jobs_with_queue_position(client, db_session, project_payload):
    project = client.post("/projects", json=project_payload).json()
    create_job(db_session, "keyframe", project["id"])
    create_job(db_session, "keyframe", project["id"])
    db_session.commit()

    res = client.get(f"/projects/{project['id']}/jobs")
    assert res.status_code == 200
    jobs = res.json()
    assert len(jobs) == 2
    positions = sorted(j["queuePosition"] for j in jobs)
    assert positions == [1, 2]


def test_get_unknown_job_returns_404(client):
    assert client.get("/jobs/nope").status_code == 404
