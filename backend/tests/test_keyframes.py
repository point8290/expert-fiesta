"""Tests for P2-S4 — Scene keyframes (and P2-S5 anchor injection)."""
import json
from pathlib import Path

import pytest

from app.dependencies import (
    get_audio_analyzer,
    get_image_generator,
    get_llm_client,
    get_storage,
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
CHARACTERS = {
    "characters": [
        {
            "name": "Aarav",
            "age": "10",
            "face": "round face",
            "hair": "messy black hair",
            "clothing": "yellow hoodie",
            "personality": "curious",
            "identityAnchors": ["yellow hoodie", "messy black hair"],
        }
    ]
}


def _scene(i):
    return {
        "visualDescription": f"scene {i}",
        "cameraInstruction": "static",
        "motionInstruction": "none",
        "keyframePrompt": "rooftop at sunset, two friends",
        "videoPrompt": "vid",
        "negativePrompt": "blurry, watermark",
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
        self.calls = []

    def generate(self, workflow, params, output_path):
        self.calls.append(
            {"workflow": workflow, "params": params, "output": output_path}
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x89PNG")
        return output_path

    def smoke_test(self):
        return ["character", "keyframe"]


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    gen = FakeImageGen()
    client.app.dependency_overrides[get_image_generator] = lambda: gen

    project = client.post("/projects", json=project_payload).json()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps(CHARACTERS)
    )
    client.post(f"/projects/{project['id']}/characters")
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_scene(i) for i in range(8)]})
    )
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    return tmp_path, gen, project, scenes


def test_generate_keyframe_creates_image(client, setup):
    # AC1: one keyframe per scene via ComfyUI.
    _, gen, _, scenes = setup
    res = client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    assert res.status_code == 200
    body = res.json()
    assert body["keyframeStatus"] == "generated"
    assert Path(body["keyframePath"]).exists()
    assert gen.calls[0]["workflow"] == "keyframe"


def test_keyframe_prompt_includes_scene_and_anchors(client, setup):
    # P2-S4 AC1 + P2-S5 AC1: prompt = keyframePrompt + identity anchors.
    _, gen, _, scenes = setup
    client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    params = gen.calls[0]["params"]
    assert "rooftop at sunset" in params["POSITIVE_PROMPT"]
    assert "yellow hoodie" in params["POSITIVE_PROMPT"]
    assert "blurry" in params["NEGATIVE_PROMPT"]


def test_approve_keyframe(client, setup):
    _, _, _, scenes = setup
    client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    res = client.post(f"/scenes/{scenes[0]['id']}/keyframe/approve")
    assert res.status_code == 200
    assert res.json()["keyframeStatus"] == "approved"


def test_upload_keyframe_replaces_manually(client, setup):
    _, _, _, scenes = setup
    res = client.post(
        f"/scenes/{scenes[0]['id']}/keyframe/upload",
        files={"file": ("kf.png", b"\x89PNGx", "image/png")},
    )
    assert res.status_code == 200
    assert res.json()["keyframeStatus"] == "approved"
    assert Path(res.json()["keyframePath"]).exists()


def test_upload_keyframe_rejects_non_image(client, setup):
    _, _, _, scenes = setup
    res = client.post(
        f"/scenes/{scenes[0]['id']}/keyframe/upload",
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert res.status_code == 415


def test_keyframe_unknown_scene_returns_404(client, setup):
    assert client.post("/scenes/nope/keyframe").status_code == 404
