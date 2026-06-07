"""Tests for P5-S4 — Cloud fallback (per-scene backend override)."""
import json
from pathlib import Path

import pytest

from app.dependencies import (
    get_audio_analyzer,
    get_image_generator,
    get_llm_client,
    get_storage,
    get_video_registry,
)
from app.schemas import AudioAnalysis
from app.storage import Storage
from app.video.registry import VIDEO_BACKENDS


def test_registry_includes_cloud_backend():
    assert "cloud" in VIDEO_BACKENDS


ANALYSIS = AudioAnalysis(
    durationSeconds=40.0, bpm=90.0, beats=[0.0, 20.0, 40.0],
    sections=[{"name": "intro", "start": 0.0, "end": 40.0}], waveform=[0.1],
)


def _scene(i):
    return {
        "visualDescription": f"s{i}", "cameraInstruction": "static",
        "motionInstruction": "drift", "keyframePrompt": "rooftop",
        "videoPrompt": "push-in", "negativePrompt": "blurry",
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
    def generate(self, workflow, params, output_path):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x89PNG")
        return output_path

    def smoke_test(self):
        return ["character", "keyframe"]


class RecordingBackend:
    def __init__(self, name):
        self.name = name
        self.workflow = name
        self.called = False

    def generate(self, keyframe_path, video_prompt, negative_prompt, output_path, *, seed=None, frames=120):
        self.called = True
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x00mp4")
        return output_path


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_image_generator] = lambda: FakeImageGen()
    registry = {
        "ltx": RecordingBackend("ltx"),
        "cloud": RecordingBackend("cloud"),
    }
    client.app.dependency_overrides[get_video_registry] = lambda: registry

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
    return client, scenes, registry


def _approve_keyframe(client, sid):
    client.post(f"/scenes/{sid}/keyframe")
    client.post(f"/scenes/{sid}/keyframe/approve")


def test_scene_override_routes_to_cloud(setup):
    client, scenes, registry = setup
    sid = scenes[0]["id"]
    patched = client.patch(f"/scenes/{sid}", json={"videoBackendOverride": "cloud"})
    assert patched.json()["videoBackendOverride"] == "cloud"

    _approve_keyframe(client, sid)
    client.post(f"/scenes/{sid}/clip/generate")
    assert registry["cloud"].called is True
    assert registry["ltx"].called is False


def test_no_override_uses_project_backend(setup):
    client, scenes, registry = setup
    sid = scenes[0]["id"]
    _approve_keyframe(client, sid)
    client.post(f"/scenes/{sid}/clip/generate")
    assert registry["ltx"].called is True
    assert registry["cloud"].called is False
