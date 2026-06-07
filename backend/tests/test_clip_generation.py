"""Tests for P3-S2 (generate scene clips) and P3-S3 (approve)."""
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
        "videoPrompt": "slow push-in, birds",
        "negativePrompt": "flicker",
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

    def __init__(self):
        self.calls = []

    def generate(
        self,
        keyframe_path,
        video_prompt,
        negative_prompt,
        output_path,
        *,
        seed=None,
        frames=120,
    ):
        self.calls.append(
            {
                "keyframe": keyframe_path,
                "video_prompt": video_prompt,
                "frames": frames,
            }
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x00\x00mp4")
        return output_path


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_image_generator] = lambda: FakeImageGen()
    backend = FakeVideoBackend()
    client.app.dependency_overrides[get_video_registry] = lambda: {"ltx": backend}

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
    return backend, project, scenes


def _approve_keyframe(client, scene_id):
    client.post(f"/scenes/{scene_id}/keyframe")
    client.post(f"/scenes/{scene_id}/keyframe/approve")


def test_generate_clip_requires_approved_keyframe(client, setup):
    _, _, scenes = setup
    res = client.post(f"/scenes/{scenes[0]['id']}/clip/generate")
    assert res.status_code == 409


def test_generate_clip_produces_clip_and_succeeds(client, setup):
    # AC1/AC2: approved keyframe -> ~5s clip; clip persists with status.
    backend, _, scenes = setup
    _approve_keyframe(client, scenes[0]["id"])

    res = client.post(f"/scenes/{scenes[0]['id']}/clip/generate")
    assert res.status_code == 200
    job = res.json()
    assert job["type"] == "clip"
    assert job["status"] == "succeeded"
    assert Path(job["resultPath"]).exists()

    scene = client.get(f"/scenes/{scenes[0]['id']}").json()
    assert scene["clipStatus"] == "generated"
    assert scene["clipPath"]
    assert backend.calls[0]["video_prompt"] == "slow push-in, birds"


def test_generate_clip_creates_job_record(client, setup):
    _, project, scenes = setup
    _approve_keyframe(client, scenes[0]["id"])
    client.post(f"/scenes/{scenes[0]['id']}/clip/generate")

    jobs = client.get(f"/projects/{project['id']}/jobs").json()
    assert any(j["type"] == "clip" for j in jobs)


def test_approve_generated_clip(client, setup):
    # P3-S3: approve a generated clip.
    _, _, scenes = setup
    _approve_keyframe(client, scenes[0]["id"])
    client.post(f"/scenes/{scenes[0]['id']}/clip/generate")

    res = client.post(f"/scenes/{scenes[0]['id']}/clip/approve")
    assert res.status_code == 200
    assert res.json()["clipStatus"] == "approved"


def test_generate_clip_unknown_scene_returns_404(client, setup):
    assert client.post("/scenes/nope/clip/generate").status_code == 404
