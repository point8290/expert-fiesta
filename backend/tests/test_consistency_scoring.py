"""Tests for P4-S4 — Consistency scoring + LoRA."""
import json
from pathlib import Path

import pytest

from app.dependencies import (
    get_audio_analyzer,
    get_consistency_scorer,
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
            "identityAnchors": ["yellow hoodie"],
        }
    ]
}


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
    def __init__(self):
        self.calls = []

    def generate(self, workflow, params, output_path):
        self.calls.append({"workflow": workflow, "params": params})
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x89PNG")
        return output_path

    def smoke_test(self):
        return ["character", "keyframe"]


class FakeScorer:
    def score(self, reference_path, candidate_path):
        return 0.87


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    gen = FakeImageGen()
    client.app.dependency_overrides[get_image_generator] = lambda: gen
    client.app.dependency_overrides[get_consistency_scorer] = lambda: FakeScorer()

    project = client.post("/projects", json=project_payload).json()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps(CHARACTERS)
    )
    char = client.post(f"/projects/{project['id']}/characters").json()[0]
    client.post(f"/characters/{char['id']}/reference")
    client.post(f"/characters/{char['id']}/reference/approve")
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_scene(i) for i in range(8)]})
    )
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    return client, project, char, scenes, gen


def test_consistency_scores_per_scene_and_character(setup):
    # AC1: face-embedding similarity score per character across scenes.
    client, project, char, scenes, _ = setup
    client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    client.post(f"/scenes/{scenes[1]['id']}/keyframe")

    res = client.get(f"/projects/{project['id']}/consistency")
    assert res.status_code == 200
    scores = res.json()
    # Two scenes have keyframes, one character with an approved reference.
    assert len(scores) == 2
    assert all(s["characterId"] == char["id"] for s in scores)
    assert all(s["score"] == 0.87 for s in scores)


def test_lora_path_is_editable(setup):
    # AC2: optional per-character LoRA path.
    client, _, char, _, _ = setup
    res = client.patch(
        f"/characters/{char['id']}", json={"loraPath": "/loras/aarav.safetensors"}
    )
    assert res.status_code == 200
    assert res.json()["loraPath"] == "/loras/aarav.safetensors"


def test_keyframe_includes_lora_when_set(setup):
    client, _, char, scenes, gen = setup
    client.patch(
        f"/characters/{char['id']}", json={"loraPath": "/loras/aarav.safetensors"}
    )
    client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    assert gen.calls[-1]["params"]["LORA_PATH"] == "/loras/aarav.safetensors"
