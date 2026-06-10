"""Tests for CB-3 — keyframe + character-ref generation run async via the worker."""
import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.dependencies import (
    get_audio_analyzer,
    get_image_generator,
    get_llm_client,
    get_storage,
)
from app.schemas import AudioAnalysis
from app.storage import Storage
from app.worker import JOB_HANDLERS


ANALYSIS = AudioAnalysis(
    durationSeconds=40.0, bpm=90.0, beats=[0.0, 20.0, 40.0],
    sections=[{"name": "intro", "start": 0.0, "end": 40.0}], waveform=[0.1],
)
CHARACTERS = {"characters": [{"name": "Aarav", "identityAnchors": ["yellow hoodie"]}]}


def _scene(i):
    return {
        "visualDescription": f"s{i}", "cameraInstruction": "static",
        "motionInstruction": "drift", "keyframePrompt": "rooftop",
        "videoPrompt": "vid", "negativePrompt": "blurry",
    }


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, prompt):
        return self.payload


class _Analyzer:
    def analyze(self, path):
        return ANALYSIS


class FakeImageGen:
    def __init__(self):
        self.calls = 0

    def generate(self, workflow, params, output_path):
        self.calls += 1
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x89PNG")
        return output_path

    def smoke_test(self):
        return ["character", "keyframe"]


@pytest.fixture()
def async_mode(monkeypatch):
    monkeypatch.setenv("ASYNC_JOBS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def project_with_scene(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_image_generator] = lambda: FakeImageGen()
    project = client.post("/projects", json=project_payload).json()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_scene(i) for i in range(8)]})
    )
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    return project, scenes


def test_worker_has_keyframe_and_character_ref_handlers():
    assert "keyframe" in JOB_HANDLERS
    assert "character_ref" in JOB_HANDLERS


def test_keyframe_enqueues_in_async_mode(client, project_with_scene, async_mode):
    _, scenes = project_with_scene
    sid = scenes[0]["id"]
    res = client.post(f"/scenes/{sid}/keyframe")
    assert res.status_code == 200
    assert res.json()["keyframeStatus"] == "generating"
    # Not produced yet — the worker hasn't run.
    assert res.json()["keyframePath"] is None
    jobs = client.get(f"/projects/{scenes[0]['projectId']}/jobs").json()
    assert any(j["type"] == "keyframe" for j in jobs)


def test_character_ref_enqueues_in_async_mode(client, tmp_path, project_payload, async_mode):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_image_generator] = lambda: FakeImageGen()
    project = client.post("/projects", json=project_payload).json()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(json.dumps(CHARACTERS))
    char = client.post(f"/projects/{project['id']}/characters").json()[0]

    res = client.post(f"/characters/{char['id']}/reference")
    assert res.status_code == 200
    assert res.json()["refStatus"] == "generating"
    jobs = client.get(f"/projects/{project['id']}/jobs").json()
    assert any(j["type"] == "character_ref" for j in jobs)


def test_keyframe_inline_when_sync(client, project_with_scene):
    # Default (ASYNC_JOBS unset) still runs inline and produces the asset.
    _, scenes = project_with_scene
    res = client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    assert res.json()["keyframeStatus"] == "generated"
    assert res.json()["keyframePath"]
