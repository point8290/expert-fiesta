"""Tests for P4-S6 — Beat-synced cuts."""
import pytest

from app.dependencies import get_audio_analyzer, get_storage
from app.schemas import AudioAnalysis
from app.services.beat_cuts import suggest_cuts
from app.storage import Storage


BEATS = [0.0, 4.8, 9.6, 14.5, 19.8, 25.1, 29.7, 35.2, 40.4, 45.6, 50.3, 55.1, 60.0]
ANALYSIS = AudioAnalysis(
    durationSeconds=60.0,
    bpm=92.0,
    beats=BEATS,
    sections=[{"name": "intro", "start": 0.0, "end": 60.0}],
    waveform=[0.1],
)


class _Analyzer:
    def analyze(self, path):
        return ANALYSIS


def test_suggest_cuts_snaps_to_beats():
    cuts = suggest_cuts(BEATS, 60.0, segments=4)
    # 4 segments -> 3 interior cut points at ~15/30/45 snapped to nearest beat.
    assert cuts == [14.5, 29.7, 45.6]
    assert all(c in BEATS for c in cuts)


def test_suggest_cuts_handles_no_beats():
    assert suggest_cuts([], 60.0, segments=4) == []
    assert suggest_cuts(BEATS, 60.0, segments=1) == []


@pytest.fixture()
def project_with_beats(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_audio_analyzer] = lambda: _Analyzer()
    project = client.post("/projects", json=project_payload).json()
    client.post(
        f"/projects/{project['id']}/audio",
        files={"file": ("song.wav", b"RIFFx", "audio/wav")},
    )
    client.post(f"/projects/{project['id']}/audio/analyze")
    return project


def test_beat_cuts_endpoint(client, project_with_beats):
    project = project_with_beats
    res = client.get(f"/projects/{project['id']}/beat-cuts?segments=4")
    assert res.status_code == 200
    cuts = res.json()["cuts"]
    assert cuts == [14.5, 29.7, 45.6]
    assert cuts == sorted(cuts)


def test_beat_cuts_requires_analyzed_audio(client, project_payload):
    project = client.post("/projects", json=project_payload).json()
    assert client.get(f"/projects/{project['id']}/beat-cuts").status_code == 404
