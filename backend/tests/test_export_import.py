"""Tests for P5-S3 — Project export / import."""
from app.models import Character, Lyrics, Project, Scene


def _seed(db_session, payload):
    project = Project(
        title=payload["title"],
        idea=payload["idea"],
        genre=payload["genre"],
        mood=payload["mood"],
        visual_style=payload["visualStyle"],
        target_duration=payload["targetDuration"],
        aspect_ratio=payload["aspectRatio"],
        video_backend="wan",
        transition="crossfade",
    )
    db_session.add(project)
    db_session.commit()
    db_session.add(
        Lyrics(
            project_id=project.id,
            title="Wings",
            structure=["intro", "chorus"],
            body="la la la",
            music_prompt="cinematic",
            emotional_arc="hopeful",
        )
    )
    db_session.add(
        Character(
            project_id=project.id,
            name="Aarav",
            identity_anchors=["yellow hoodie"],
            lora_path="/loras/aarav.safetensors",
        )
    )
    db_session.add_all(
        [
            Scene(
                project_id=project.id, number=n, start_time=0, end_time=5,
                duration_seconds=5, keyframe_prompt=f"kf {n}", video_prompt="v",
                negative_prompt="blurry",
            )
            for n in (1, 2, 3)
        ]
    )
    db_session.commit()
    return project


def test_export_project(client, db_session, project_payload):
    project = _seed(db_session, project_payload)
    res = client.get(f"/projects/{project.id}/export")
    assert res.status_code == 200
    exp = res.json()
    assert exp["project"]["title"] == project_payload["title"]
    assert exp["project"]["videoBackend"] == "wan"
    assert exp["lyrics"]["title"] == "Wings"
    assert len(exp["characters"]) == 1
    assert len(exp["scenes"]) == 3


def test_export_unknown_project_returns_404(client):
    assert client.get("/projects/nope/export").status_code == 404


def test_import_recreates_project_with_new_id(client, db_session, project_payload):
    project = _seed(db_session, project_payload)
    exported = client.get(f"/projects/{project.id}/export").json()

    res = client.post("/projects/import", json=exported)
    assert res.status_code == 201
    new = res.json()
    assert new["id"] != project.id
    assert new["title"] == project_payload["title"]
    assert new["videoBackend"] == "wan"
    assert new["transition"] == "crossfade"

    assert len(client.get(f"/projects/{new['id']}/scenes").json()) == 3
    chars = client.get(f"/projects/{new['id']}/characters").json()
    assert len(chars) == 1
    assert chars[0]["loraPath"] == "/loras/aarav.safetensors"
    assert client.get(f"/projects/{new['id']}/lyrics").json()["title"] == "Wings"


def test_import_resets_generated_assets(client, db_session, project_payload):
    project = _seed(db_session, project_payload)
    exported = client.get(f"/projects/{project.id}/export").json()
    new = client.post("/projects/import", json=exported).json()
    # Assets aren't copied; imported scenes start fresh.
    scenes = client.get(f"/projects/{new['id']}/scenes").json()
    assert all(s["keyframeStatus"] == "pending" for s in scenes)
    assert all(s["clipStatus"] == "pending" for s in scenes)
