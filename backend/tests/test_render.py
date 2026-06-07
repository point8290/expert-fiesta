"""Tests for P1-S8 — Render final MP4."""
import json
from pathlib import Path

import pytest

from app.dependencies import (
    get_audio_analyzer,
    get_llm_client,
    get_renderer,
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


class _Analyzer:
    def analyze(self, path):
        return ANALYSIS


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, prompt):
        return self.payload


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def render(self, clips, audio_path, output_path, *, width, height, fps, **_):
        self.calls.append(
            {"clips": list(clips), "audio": audio_path, "output": output_path}
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"FAKEMP4")
        return output_path


def _content(i):
    return {
        "visualDescription": f"s{i}",
        "cameraInstruction": "static",
        "motionInstruction": "none",
        "keyframePrompt": "kf",
        "videoPrompt": "vid",
        "negativePrompt": "blurry",
    }


@pytest.fixture()
def renderer(client):
    fake = FakeRenderer()
    client.app.dependency_overrides[get_renderer] = lambda: fake
    return fake


@pytest.fixture()
def project_with_clips(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(
        json.dumps({"scenes": [_content(i) for i in range(8)]})
    )
    project = client.post("/projects", json=project_payload).json()
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    scenes = client.post(f"/projects/{project['id']}/storyboard").json()

    def upload_all():
        for sc in scenes:
            client.post(
                f"/scenes/{sc['id']}/clip",
                files={"file": ("clip.mp4", b"\x00mp4", "video/mp4")},
            )

    return project, scenes, upload_all


def test_render_produces_output(client, project_with_clips, renderer):
    # AC1/AC2: render over approved clips writes final.mp4.
    project, _, upload_all = project_with_clips
    upload_all()

    res = client.post(f"/projects/{project['id']}/render")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["outputPath"].endswith("final.mp4")
    assert Path(body["outputPath"]).exists()


def test_render_calls_adapter_with_ordered_clips_and_audio(
    client, project_with_clips, renderer
):
    # AC3: render goes through the mockable adapter, clips in scene order.
    project, scenes, upload_all = project_with_clips
    upload_all()

    client.post(f"/projects/{project['id']}/render")
    assert len(renderer.calls) == 1
    call = renderer.calls[0]
    assert len(call["clips"]) == len(scenes)
    assert call["audio"].endswith("song.wav")
    # Clip order follows scene numbering: i-th clip belongs to the i-th scene.
    for clip_path, scene in zip(call["clips"], scenes):
        assert scene["id"] in clip_path


def test_render_with_unapproved_clip_returns_error(
    client, project_with_clips, renderer
):
    # AC4: missing/unapproved clips -> clear error, no render.
    project, scenes, _ = project_with_clips
    # Upload clips for all but the last scene.
    for sc in scenes[:-1]:
        client.post(
            f"/scenes/{sc['id']}/clip",
            files={"file": ("clip.mp4", b"x", "video/mp4")},
        )
    res = client.post(f"/projects/{project['id']}/render")
    assert res.status_code == 409
    assert renderer.calls == []


def test_render_unknown_project_returns_404(client, renderer):
    assert client.post("/projects/nope/render").status_code == 404
