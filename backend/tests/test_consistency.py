"""Tests for P2-S5 — Character consistency (IP-Adapter wiring)."""
import json
from pathlib import Path

import pytest

from app.comfyui.client import ComfyUIClient
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
            "identityAnchors": ["yellow hoodie"],
        }
    ]
}


def _scene(i):
    return {
        "visualDescription": f"scene {i}",
        "cameraInstruction": "static",
        "motionInstruction": "none",
        "keyframePrompt": "rooftop",
        "videoPrompt": "vid",
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
        return ComfyUIClient().smoke_test()


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
    char = client.post(f"/projects/{project['id']}/characters").json()[0]
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_scene(i) for i in range(8)]})
    )
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    return gen, project, char, scenes


def test_ipadapter_workflow_template_exists():
    # AC2: an IP-Adapter keyframe workflow is committed.
    assert "keyframe_ipadapter" in ComfyUIClient().smoke_test()


def test_keyframe_uses_ipadapter_when_reference_approved(client, setup):
    # AC2: with an approved character reference, the keyframe uses IP-Adapter and
    # passes that reference image into the workflow.
    gen, _, char, scenes = setup
    client.post(f"/characters/{char['id']}/reference")
    client.post(f"/characters/{char['id']}/reference/approve")

    client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    call = gen.calls[-1]
    assert call["workflow"] == "keyframe_ipadapter"
    assert call["params"]["REFERENCE_IMAGE"].endswith(".png")


def test_keyframe_without_reference_uses_plain_workflow(client, setup):
    gen, _, _, scenes = setup
    client.post(f"/scenes/{scenes[0]['id']}/keyframe")
    call = gen.calls[-1]
    assert call["workflow"] == "keyframe"
    assert "REFERENCE_IMAGE" not in call["params"]
