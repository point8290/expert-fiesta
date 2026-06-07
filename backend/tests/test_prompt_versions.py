"""Tests for P4-S3 — Prompt versioning."""
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


ANALYSIS = AudioAnalysis(
    durationSeconds=40.0,
    bpm=90.0,
    beats=[0.0, 20.0, 40.0],
    sections=[{"name": "intro", "start": 0.0, "end": 40.0}],
    waveform=[0.1],
)


def _scene(i):
    return {
        "visualDescription": f"scene {i}",
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


class FakeVideoBackend:
    workflow = "fake"

    def generate(self, keyframe_path, video_prompt, negative_prompt, output_path, *, seed=None, frames=120):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x00mp4")
        return output_path


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_image_generator] = lambda: FakeImageGen()
    client.app.dependency_overrides[get_video_registry] = lambda: {
        "ltx": FakeVideoBackend()
    }

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
    return client, project, scenes


def test_storyboard_creates_initial_version(setup):
    client, _, scenes = setup
    res = client.get(f"/scenes/{scenes[0]['id']}/prompt-versions")
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["keyframePrompt"] == "rooftop"


def test_editing_prompt_creates_new_version(setup):
    client, _, scenes = setup
    sid = scenes[0]["id"]
    client.patch(f"/scenes/{sid}", json={"keyframePrompt": "sunset rooftop"})
    versions = client.get(f"/scenes/{sid}/prompt-versions").json()
    assert len(versions) == 2
    latest = max(versions, key=lambda v: v["version"])
    assert latest["version"] == 2
    assert latest["keyframePrompt"] == "sunset rooftop"


def test_editing_non_prompt_field_does_not_version(setup):
    # Editing only camera/motion (still prompt-ish) — but a no-op patch shouldn't
    # create a version. Patch with the same keyframePrompt value.
    client, _, scenes = setup
    sid = scenes[0]["id"]
    client.patch(f"/scenes/{sid}", json={"cameraInstruction": "pan"})
    versions = client.get(f"/scenes/{sid}/prompt-versions").json()
    assert len(versions) == 1  # camera instruction isn't a generation prompt


def test_regenerate_prompt_creates_new_version(setup):
    client, _, scenes = setup
    sid = scenes[0]["id"]
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps(
            {
                "visualDescription": "regen",
                "cameraInstruction": "pan",
                "motionInstruction": "drift",
                "keyframePrompt": "regen kf",
                "videoPrompt": "regen vid",
                "negativePrompt": "noise",
            }
        )
    )
    client.post(f"/scenes/{sid}/regenerate-prompt")
    versions = client.get(f"/scenes/{sid}/prompt-versions").json()
    assert len(versions) == 2
    assert max(versions, key=lambda v: v["version"])["keyframePrompt"] == "regen kf"


def test_keyframe_records_prompt_version(setup):
    client, _, scenes = setup
    sid = scenes[0]["id"]
    client.patch(f"/scenes/{sid}", json={"keyframePrompt": "v2 prompt"})  # -> v2
    scene = client.post(f"/scenes/{sid}/keyframe").json()
    assert scene["keyframePromptVersion"] == 2


def test_clip_records_prompt_version(setup):
    client, _, scenes = setup
    sid = scenes[0]["id"]
    client.post(f"/scenes/{sid}/keyframe")
    client.post(f"/scenes/{sid}/keyframe/approve")
    client.post(f"/scenes/{sid}/clip/generate")
    scene = client.get(f"/scenes/{sid}").json()
    assert scene["clipPromptVersion"] == 1
