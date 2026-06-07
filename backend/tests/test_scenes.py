"""Tests for P1-S6 — Manage scenes."""
import json

import pytest

from app.dependencies import get_audio_analyzer, get_llm_client, get_storage
from app.schemas import AudioAnalysis
from app.storage import Storage


ANALYSIS = AudioAnalysis(
    durationSeconds=60.0,
    bpm=90.0,
    beats=[0.0, 5.0, 10.0, 60.0],
    sections=[{"name": "intro", "start": 0.0, "end": 60.0}],
    waveform=[0.1],
)


def _scene_content(i):
    return {
        "visualDescription": f"scene {i}",
        "cameraInstruction": "static",
        "motionInstruction": "none",
        "keyframePrompt": f"kf {i}",
        "videoPrompt": f"vid {i}",
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


@pytest.fixture()
def project_with_scenes(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_scene_content(i) for i in range(10)]})
    )
    project = client.post("/projects", json=project_payload).json()
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    return project, scenes


def test_patch_scene_edits_prompt_fields(client, project_with_scenes):
    # AC2: editing prompt fields persists.
    _, scenes = project_with_scenes
    scene = scenes[0]
    res = client.patch(
        f"/scenes/{scene['id']}",
        json={"visualDescription": "new look", "keyframePrompt": "new kf"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["visualDescription"] == "new look"
    assert body["keyframePrompt"] == "new kf"


def test_patch_scene_preserves_timing(client, project_with_scenes):
    _, scenes = project_with_scenes
    scene = scenes[0]
    res = client.patch(
        f"/scenes/{scene['id']}", json={"visualDescription": "x"}
    ).json()
    assert res["startTime"] == scene["startTime"]
    assert res["endTime"] == scene["endTime"]


def test_patch_unknown_scene_returns_404(client, project_with_scenes):
    assert client.patch("/scenes/nope", json={"visualDescription": "x"}).status_code == 404


def test_regenerate_prompt_updates_content_keeps_timing(client, project_with_scenes):
    # AC3: regenerate prompts for a single scene.
    project, scenes = project_with_scenes
    scene = scenes[0]
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps(
            {
                "visualDescription": "regenerated",
                "cameraInstruction": "pan",
                "motionInstruction": "drift",
                "keyframePrompt": "regen kf",
                "videoPrompt": "regen vid",
                "negativePrompt": "noise",
            }
        )
    )
    res = client.post(f"/scenes/{scene['id']}/regenerate-prompt")
    assert res.status_code == 200
    body = res.json()
    assert body["visualDescription"] == "regenerated"
    assert body["startTime"] == scene["startTime"]
    assert body["number"] == scene["number"]


def test_regenerate_unknown_scene_returns_404(client, project_with_scenes):
    assert client.post("/scenes/nope/regenerate-prompt").status_code == 404
