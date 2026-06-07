"""Tests for P4-S1 (Wan 2.2) and P4-S2 (HunyuanVideo) backends + selection."""
import json
from pathlib import Path

import pytest

from app.comfyui.client import ComfyUIClient
from app.dependencies import (
    get_audio_analyzer,
    get_image_generator,
    get_llm_client,
    get_storage,
    get_video_registry,
)
from app.schemas import AudioAnalysis
from app.storage import Storage
from app.video.backends import HunyuanBackend, LTXBackend, WanBackend
from app.video.registry import VIDEO_BACKENDS, build_video_backend


def test_wan_and_hunyuan_templates_committed():
    names = ComfyUIClient().smoke_test()
    assert "wan_video" in names
    assert "hunyuan_video" in names


def test_build_video_backend_returns_correct_class():
    assert isinstance(build_video_backend("ltx"), LTXBackend)
    assert isinstance(build_video_backend("wan"), WanBackend)
    assert isinstance(build_video_backend("hunyuan"), HunyuanBackend)
    assert build_video_backend("wan").workflow == "wan_video"
    assert build_video_backend("hunyuan").workflow == "hunyuan_video"


def test_registry_lists_all_backends():
    assert set(VIDEO_BACKENDS) == {"ltx", "wan", "hunyuan"}


def test_build_unknown_backend_raises():
    with pytest.raises(KeyError):
        build_video_backend("nope")


# --- selection per project --------------------------------------------------

ANALYSIS = AudioAnalysis(
    durationSeconds=40.0,
    bpm=90.0,
    beats=[0.0, 20.0, 40.0],
    sections=[{"name": "intro", "start": 0.0, "end": 40.0}],
    waveform=[0.1],
)


def _scene(i):
    return {
        "visualDescription": f"s{i}",
        "cameraInstruction": "static",
        "motionInstruction": "drift",
        "keyframePrompt": "rooftop",
        "videoPrompt": "push-in",
        "negativePrompt": "blurry",
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
        "wan": RecordingBackend("wan"),
        "hunyuan": RecordingBackend("hunyuan"),
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
    return client, project, scenes, registry


def test_project_defaults_to_ltx_backend(setup):
    client, project, _, _ = setup
    assert client.get(f"/projects/{project['id']}").json()["videoBackend"] == "ltx"


def test_video_backend_is_selectable_per_project(setup):
    client, project, scenes, registry = setup
    # Select Wan for this project.
    patched = client.patch(
        f"/projects/{project['id']}", json={"videoBackend": "wan"}
    )
    assert patched.json()["videoBackend"] == "wan"

    sid = scenes[0]["id"]
    client.post(f"/scenes/{sid}/keyframe")
    client.post(f"/scenes/{sid}/keyframe/approve")
    client.post(f"/scenes/{sid}/clip/generate")

    assert registry["wan"].called is True
    assert registry["ltx"].called is False


def test_unknown_project_backend_returns_400(setup):
    client, project, scenes, _ = setup
    # Force an invalid backend directly via the API.
    client.patch(f"/projects/{project['id']}", json={"videoBackend": "bogus"})
    sid = scenes[0]["id"]
    client.post(f"/scenes/{sid}/keyframe")
    client.post(f"/scenes/{sid}/keyframe/approve")
    res = client.post(f"/scenes/{sid}/clip/generate")
    assert res.status_code == 400
