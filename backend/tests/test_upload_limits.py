"""Tests for PR0-7 — configurable upload size cap (413 when exceeded)."""
import pytest

from app.config import get_settings


@pytest.fixture()
def project(client, project_payload):
    return client.post("/projects", json=project_payload).json()


def test_audio_upload_rejected_over_cap(client, project, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")  # 0 MB → anything non-empty is too big
    get_settings.cache_clear()
    try:
        res = client.post(
            f"/projects/{project['id']}/audio",
            files={"file": ("s.wav", b"RIFFdata", "audio/wav")},
        )
        assert res.status_code == 413
    finally:
        get_settings.cache_clear()


def test_audio_upload_allowed_under_cap(client, project, tmp_path):
    from app.dependencies import get_storage
    from app.storage import Storage

    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    res = client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("s.wav", b"RIFFdata", "audio/wav")},
    )
    assert res.status_code == 201  # default cap (100 MB) allows it
