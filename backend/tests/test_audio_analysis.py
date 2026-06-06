"""Tests for P1-S4 — Analyze audio."""
import pytest

from app.dependencies import get_audio_analyzer, get_storage
from app.schemas import AudioAnalysis
from app.storage import Storage


ANALYSIS = AudioAnalysis(
    durationSeconds=60.0,
    bpm=92.0,
    beats=[0.0, 0.65, 1.30, 1.95],
    sections=[
        {"name": "intro", "start": 0.0, "end": 8.0},
        {"name": "verse", "start": 8.0, "end": 30.0},
        {"name": "chorus", "start": 30.0, "end": 60.0},
    ],
    waveform=[0.0, 0.4, 0.8, 0.2],
)


class FakeAnalyzer:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def analyze(self, path):
        self.calls.append(path)
        return self.result


@pytest.fixture()
def setup(client, tmp_path):
    """Override storage + analyzer; return the FakeAnalyzer for assertions."""
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    fake = FakeAnalyzer(ANALYSIS)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: fake
    return fake


def _project_with_audio(client, project_payload):
    project = client.post("/projects", json=project_payload).json()
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFdata", "audio/wav")},
    )
    return project


def test_analyze_returns_features(client, project_payload, setup):
    # AC1: returns duration, bpm, beats, sections, waveform.
    project = _project_with_audio(client, project_payload)
    res = client.post(f"/projects/{project['id']}/audio/analyze")
    assert res.status_code == 200
    body = res.json()
    assert body["durationSeconds"] == 60.0
    assert body["bpm"] == 92.0
    assert body["beats"] == [0.0, 0.65, 1.30, 1.95]
    assert body["sections"][0]["name"] == "intro"
    assert body["waveform"]


def test_analyze_calls_adapter_with_stored_path(client, project_payload, setup):
    # AC2: analysis runs behind a mockable adapter, given the stored file path.
    project = _project_with_audio(client, project_payload)
    client.post(f"/projects/{project['id']}/audio/analyze")
    assert len(setup.calls) == 1
    assert setup.calls[0].endswith("song.wav")


def test_analysis_persists_on_audio_record(client, project_payload, setup):
    # AC3: results persist; GET /audio returns the analysis.
    project = _project_with_audio(client, project_payload)
    client.post(f"/projects/{project['id']}/audio/analyze")
    res = client.get(f"/projects/{project['id']}/audio")
    assert res.json()["bpm"] == 92.0
    assert res.json()["durationSeconds"] == 60.0


def test_analyze_without_audio_returns_404(client, project_payload, setup):
    project = client.post("/projects", json=project_payload).json()
    res = client.post(f"/projects/{project['id']}/audio/analyze")
    assert res.status_code == 404


def test_analyze_unknown_project_returns_404(client, setup):
    res = client.post("/projects/nope/audio/analyze")
    assert res.status_code == 404
