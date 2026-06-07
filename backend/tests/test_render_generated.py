"""Tests for P3-S4 — Final render consumes generated clips (unchanged path)."""
import json
from pathlib import Path

import pytest

from app.dependencies import (
    get_audio_analyzer,
    get_image_generator,
    get_llm_client,
    get_renderer,
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
        "visualDescription": f"s{i}",
        "cameraInstruction": "static",
        "motionInstruction": "drift",
        "keyframePrompt": "rooftop",
        "videoPrompt": "push-in",
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

    def generate(self, keyframe_path, video_prompt, negative_prompt, output_path, *, seed=None, frames=120):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x00mp4")
        return output_path


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def render(self, clips, audio_path, output_path, *, width, height, fps):
        self.calls.append({"clips": list(clips)})
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"FINAL")
        return output_path


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_image_generator] = lambda: FakeImageGen()
    client.app.dependency_overrides[get_video_registry] = lambda: {
        "ltx": FakeVideoBackend()
    }
    renderer = FakeRenderer()
    client.app.dependency_overrides[get_renderer] = lambda: renderer

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
    return renderer, project, scenes


def test_render_from_generated_clips(client, setup):
    # AC1: generated -> approved clips flow through the unchanged render path.
    renderer, project, scenes = setup
    for sc in scenes:
        client.post(f"/scenes/{sc['id']}/keyframe")
        client.post(f"/scenes/{sc['id']}/keyframe/approve")
        client.post(f"/scenes/{sc['id']}/clip/generate")
        client.post(f"/scenes/{sc['id']}/clip/approve")

    res = client.post(f"/projects/{project['id']}/render")
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    assert Path(res.json()["outputPath"]).exists()
    assert len(renderer.calls[0]["clips"]) == len(scenes)
    assert all(c.endswith("clip.mp4") for c in renderer.calls[0]["clips"])
