"""Tests for P1-S3 — Upload project audio."""
import pytest

from app.dependencies import get_storage
from app.storage import Storage


@pytest.fixture()
def storage_dir(client, tmp_path):
    """Point file storage at a throwaway directory for the duration of a test."""
    storage = Storage(tmp_path)
    client.app.dependency_overrides[get_storage] = lambda: storage
    return tmp_path


def _make_project(client, project_payload):
    return client.post("/projects", json=project_payload).json()


def test_upload_audio_stores_file_and_metadata(
    client, project_payload, storage_dir
):
    # AC1: accepts a WAV upload, stores it, records source="upload".
    project = _make_project(client, project_payload)
    res = client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFfake-wav-bytes", "audio/wav")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["filename"] == "song.wav"
    assert body["source"] == "upload"

    stored = storage_dir / project["id"] / "audio" / "song.wav"
    assert stored.exists()
    assert stored.read_bytes() == b"RIFFfake-wav-bytes"


def test_upload_audio_accepts_mp3(client, project_payload, storage_dir):
    project = _make_project(client, project_payload)
    res = client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.mp3", b"ID3fake-mp3", "audio/mpeg")},
    )
    assert res.status_code == 201


def test_upload_rejects_non_audio(client, project_payload, storage_dir):
    # AC2: non-audio mime type -> 415.
    project = _make_project(client, project_payload)
    res = client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 415


def test_upload_unknown_project_returns_404(client, storage_dir):
    res = client.post(
        "/projects/nope/audio",
        files={"file": ("song.wav", b"x", "audio/wav")},
    )
    assert res.status_code == 404


def test_get_audio_returns_metadata(client, project_payload, storage_dir):
    # AC3: get returns stored audio metadata.
    project = _make_project(client, project_payload)
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"data", "audio/wav")},
    )
    res = client.get(f"/projects/{project['id']}/audio")
    assert res.status_code == 200
    assert res.json()["filename"] == "song.wav"


def test_get_audio_when_none_returns_404(client, project_payload, storage_dir):
    project = _make_project(client, project_payload)
    assert client.get(f"/projects/{project['id']}/audio").status_code == 404
