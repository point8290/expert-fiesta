"""Tests for P1-S5 — Generate storyboard."""
import json

import pytest

from app.dependencies import get_audio_analyzer, get_llm_client, get_storage
from app.schemas import AudioAnalysis
from app.storage import Storage


# Beats deliberately offset from the equal 5s divisions (5, 10, 15, ...) so that
# snapping to them is observable.
BEATS = [0.0, 4.8, 9.6, 14.5, 19.8, 25.1, 29.7, 35.2, 40.4, 45.6, 50.3, 55.1, 60.0]
SECTIONS = [
    {"name": "intro", "start": 0.0, "end": 10.0},
    {"name": "verse", "start": 10.0, "end": 40.0},
    {"name": "chorus", "start": 40.0, "end": 60.0},
]
ANALYSIS = AudioAnalysis(
    durationSeconds=60.0, bpm=92.0, beats=BEATS, sections=SECTIONS, waveform=[0.1, 0.2]
)


def _scene_content(i):
    return {
        "visualDescription": f"scene {i} description",
        "cameraInstruction": "slow push-in",
        "motionInstruction": "birds drift",
        "keyframePrompt": f"keyframe prompt {i}",
        "videoPrompt": f"video prompt {i}",
        "negativePrompt": "deformed, watermark",
    }


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, prompt):
        return self.payload


@pytest.fixture()
def setup(client, tmp_path):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    return client


class _Analyzer:
    def analyze(self, path):
        return ANALYSIS


def _install_llm(client, n_scenes):
    payload = json.dumps({"scenes": [_scene_content(i) for i in range(n_scenes)]})
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(payload)


def _project_ready(client, project_payload):
    project = client.post("/projects", json=project_payload).json()
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    return project


def test_storyboard_creates_scenes_with_all_fields(client, project_payload, setup):
    # AC1: scenes have number, times, descriptions, prompts.
    _install_llm(client, 12)
    project = _project_ready(client, project_payload)

    res = client.post(f"/projects/{project['id']}/storyboard")
    assert res.status_code == 201
    scenes = res.json()
    first = scenes[0]
    for field in (
        "number",
        "startTime",
        "endTime",
        "durationSeconds",
        "sectionName",
        "visualDescription",
        "cameraInstruction",
        "motionInstruction",
        "keyframePrompt",
        "videoPrompt",
        "negativePrompt",
    ):
        assert field in first
    assert [s["number"] for s in scenes] == list(range(1, len(scenes) + 1))


def test_scene_boundaries_snap_to_beats(client, project_payload, setup):
    # AC2: interior boundaries snap to real beats; endpoints stay at 0 and total.
    _install_llm(client, 12)
    project = _project_ready(client, project_payload)

    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    assert scenes[0]["startTime"] == 0.0
    assert scenes[-1]["endTime"] == 60.0
    beat_set = set(BEATS)
    for scene in scenes[1:]:
        assert scene["startTime"] in beat_set


def test_scene_count_and_total_duration(client, project_payload, setup):
    # AC3: count within 8-12 and total duration ~ target.
    _install_llm(client, 12)
    project = _project_ready(client, project_payload)

    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    assert 8 <= len(scenes) <= 12
    total = sum(s["durationSeconds"] for s in scenes)
    assert abs(total - 60.0) < 0.05


def test_section_names_assigned_from_analysis(client, project_payload, setup):
    _install_llm(client, 12)
    project = _project_ready(client, project_payload)

    scenes = client.post(f"/projects/{project['id']}/storyboard").json()
    assert scenes[0]["sectionName"] == "intro"
    assert scenes[-1]["sectionName"] == "chorus"


def test_storyboard_persists_and_lists_scenes(client, project_payload, setup):
    _install_llm(client, 12)
    project = _project_ready(client, project_payload)

    client.post(f"/projects/{project['id']}/storyboard")
    res = client.get(f"/projects/{project['id']}/scenes")
    assert res.status_code == 200
    assert len(res.json()) == 12


def test_storyboard_regeneration_replaces_scenes(client, project_payload, setup):
    _install_llm(client, 12)
    project = _project_ready(client, project_payload)

    client.post(f"/projects/{project['id']}/storyboard")
    client.post(f"/projects/{project['id']}/storyboard")
    res = client.get(f"/projects/{project['id']}/scenes")
    assert len(res.json()) == 12  # not 24


def test_storyboard_unknown_project_returns_404(client, setup):
    _install_llm(client, 12)
    assert client.post("/projects/nope/storyboard").status_code == 404
