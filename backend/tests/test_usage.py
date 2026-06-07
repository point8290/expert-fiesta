"""Tests for P5-S5 — Usage tracking."""
from app.models import Job, Project


def _project(db_session, payload, owner_id=None):
    project = Project(
        owner_id=owner_id,
        title=payload["title"], idea=payload["idea"], genre=payload["genre"],
        mood=payload["mood"], visual_style=payload["visualStyle"],
        target_duration=payload["targetDuration"], aspect_ratio=payload["aspectRatio"],
    )
    db_session.add(project)
    db_session.commit()
    return project


def _seed_jobs(db_session, project_id):
    db_session.add_all(
        [
            Job(project_id=project_id, type="clip", status="succeeded"),
            Job(project_id=project_id, type="clip", status="succeeded"),
            Job(project_id=project_id, type="clip", status="failed"),
            Job(project_id=project_id, type="keyframe", status="succeeded"),
        ]
    )
    db_session.commit()


def test_project_usage_summary(client, db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    _seed_jobs(db_session, project.id)

    res = client.get(f"/projects/{project.id}/usage")
    assert res.status_code == 200
    usage = res.json()
    assert usage["totalJobs"] == 4
    assert usage["succeeded"] == 3
    assert usage["failed"] == 1
    assert usage["byType"]["clip"] == 3
    assert usage["byType"]["keyframe"] == 1


def test_usage_for_project_without_jobs(client, db_session, project_payload, default_user):
    project = _project(db_session, project_payload, default_user.id)
    res = client.get(f"/projects/{project.id}/usage")
    assert res.status_code == 200
    assert res.json()["totalJobs"] == 0
    assert res.json()["byType"] == {}


def test_usage_unknown_project_returns_404(client):
    assert client.get("/projects/nope/usage").status_code == 404


def test_global_usage_summary(client, db_session, project_payload, default_user):
    p1 = _project(db_session, {**project_payload, "title": "A"}, default_user.id)
    p2 = _project(db_session, {**project_payload, "title": "B"}, default_user.id)
    _seed_jobs(db_session, p1.id)
    _seed_jobs(db_session, p2.id)

    res = client.get("/usage")
    assert res.status_code == 200
    assert res.json()["totalJobs"] == 8
    assert res.json()["byType"]["clip"] == 6
