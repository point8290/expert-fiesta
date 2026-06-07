"""Tests for PR0-6 — authenticated media serving (keyframe / clip / render)."""
import pytest

from app.dependencies import get_storage
from app.models import Project, Scene, User
from app.services.auth import hash_password
from app.storage import Storage


def _project(db_session, payload, owner_id):
    p = Project(
        owner_id=owner_id, title=payload["title"], idea=payload["idea"],
        genre=payload["genre"], mood=payload["mood"], visual_style=payload["visualStyle"],
        target_duration=payload["targetDuration"], aspect_ratio=payload["aspectRatio"],
    )
    db_session.add(p)
    db_session.commit()
    return p


def _scene(db_session, project_id, **kw):
    s = Scene(project_id=project_id, number=1, start_time=0, end_time=5,
              duration_seconds=5, **kw)
    db_session.add(s)
    db_session.commit()
    return s


def test_serve_keyframe(client, db_session, default_user, project_payload, tmp_path):
    kf = tmp_path / "k.png"
    kf.write_bytes(b"PNGDATA")
    project = _project(db_session, project_payload, default_user.id)
    scene = _scene(db_session, project.id, keyframe_path=str(kf), keyframe_status="approved")

    res = client.get(f"/scenes/{scene.id}/keyframe/file")
    assert res.status_code == 200
    assert res.content == b"PNGDATA"


def test_serve_keyframe_missing_returns_404(client, db_session, default_user, project_payload):
    project = _project(db_session, project_payload, default_user.id)
    scene = _scene(db_session, project.id)  # no keyframe_path
    assert client.get(f"/scenes/{scene.id}/keyframe/file").status_code == 404


def test_serve_clip(client, db_session, default_user, project_payload, tmp_path):
    clip = tmp_path / "c.mp4"
    clip.write_bytes(b"MP4DATA")
    project = _project(db_session, project_payload, default_user.id)
    scene = _scene(db_session, project.id, clip_path=str(clip), clip_status="approved")
    res = client.get(f"/scenes/{scene.id}/clip/file")
    assert res.status_code == 200
    assert res.content == b"MP4DATA"


def test_serve_render(client, db_session, default_user, project_payload, tmp_path):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    project = _project(db_session, project_payload, default_user.id)
    out = tmp_path / project.id / "renders" / "final.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"FINALMP4")

    res = client.get(f"/projects/{project.id}/render/file")
    assert res.status_code == 200
    assert res.content == b"FINALMP4"


def test_non_owner_gets_404(client, db_session, default_user, project_payload, tmp_path):
    other = User(email="other@example.com", hashed_password=hash_password("x"))
    db_session.add(other)
    db_session.commit()
    kf = tmp_path / "k.png"
    kf.write_bytes(b"x")
    foreign = _project(db_session, project_payload, other.id)  # owned by someone else
    scene = _scene(db_session, foreign.id, keyframe_path=str(kf))
    # client is authenticated as default_user → must not see it.
    assert client.get(f"/scenes/{scene.id}/keyframe/file").status_code == 404
