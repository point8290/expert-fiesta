"""Tests for P1-S7 — Upload clip per scene."""
import json

import pytest

from app.dependencies import get_audio_analyzer, get_llm_client, get_storage
from app.schemas import AudioAnalysis
from app.storage import Storage


ANALYSIS = AudioAnalysis(
    durationSeconds=50.0,
    bpm=90.0,
    beats=[0.0, 25.0, 50.0],
    sections=[{"name": "intro", "start": 0.0, "end": 50.0}],
    waveform=[0.1],
)


class _Analyzer:
    def analyze(self, path):
        return ANALYSIS


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, prompt):
        return self.payload


def _content(i):
    return {
        "visualDescription": f"s{i}",
        "cameraInstruction": "static",
        "motionInstruction": "none",
        "keyframePrompt": "kf",
        "videoPrompt": "vid",
        "negativePrompt": "blurry",
    }


@pytest.fixture()
def scene(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_content(i) for i in range(10)]})
    )
    project = client.post("/projects", json=project_payload).json()
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    return tmp_path, project, scenes[0]


def test_upload_clip_sets_status_approved(client, scene):
    # AC1: store uploaded clip and set clipStatus="approved".
    tmp_path, project, sc = scene
    res = client.post(
        f"/scenes/{sc['id']}/clip",
        files={"file": ("clip.mp4", b"\x00\x00mp4", "video/mp4")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["clipStatus"] == "approved"
    stored = tmp_path / project["id"] / "scenes" / sc["id"] / "clip.mp4"
    assert stored.exists()


def test_upload_clip_rejects_non_video(client, scene):
    # AC2: non-video upload -> 415.
    _, _, sc = scene
    res = client.post(
        f"/scenes/{sc['id']}/clip",
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert res.status_code == 415


def test_upload_clip_unknown_scene_returns_404(client, scene):
    res = client.post(
        "/scenes/nope/clip",
        files={"file": ("clip.mp4", b"x", "video/mp4")},
    )
    assert res.status_code == 404


def test_finalize_marks_scene_final(client, scene):
    # AC3: finalize marks the scene final.
    _, _, sc = scene
    client.post(
        f"/scenes/{sc['id']}/clip",
        files={"file": ("clip.mp4", b"x", "video/mp4")},
    )
    res = client.post(f"/scenes/{sc['id']}/finalize")
    assert res.status_code == 200
    assert res.json()["clipStatus"] == "final"


def test_finalize_unknown_scene_returns_404(client, scene):
    assert client.post("/scenes/nope/finalize").status_code == 404
