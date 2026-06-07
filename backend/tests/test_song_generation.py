"""Tests for P5-S6 — Local song generation."""
import json
from pathlib import Path

import pytest

from app.dependencies import get_llm_client, get_song_generator, get_storage
from app.storage import Storage


VALID_LYRICS = {
    "title": "Wings",
    "structure": ["intro", "chorus"],
    "body": "la la la",
    "musicPrompt": "cinematic pop rock, 90 bpm, soaring chorus",
    "emotionalArc": "hopeful",
}


class FakeLLM:
    def complete(self, system, prompt):
        return json.dumps(VALID_LYRICS)


class FakeSongGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, output_path, duration):
        self.calls.append({"prompt": prompt, "duration": duration})
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"RIFFgenerated")
        return output_path


@pytest.fixture()
def setup(client, tmp_path, project_payload):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    gen = FakeSongGenerator()
    client.app.dependency_overrides[get_song_generator] = lambda: gen
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM()
    project = client.post("/projects", json=project_payload).json()
    return client, project, gen, tmp_path


def test_generate_song_creates_audio(setup):
    client, project, gen, tmp_path = setup
    client.post(f"/projects/{project['id']}/lyrics")  # provides the music prompt

    res = client.post(f"/projects/{project['id']}/audio/generate")
    assert res.status_code == 201
    body = res.json()
    assert body["source"] == "generated"
    assert Path(
        tmp_path / project["id"] / "audio" / "song.wav"
    ).exists()
    # The generator is driven by the lyrics' music prompt + target duration.
    assert gen.calls[0]["prompt"] == VALID_LYRICS["musicPrompt"]
    assert gen.calls[0]["duration"] == project_payload_duration()


def project_payload_duration():
    return 60


def test_generate_song_requires_lyrics(setup):
    client, project, _, _ = setup
    res = client.post(f"/projects/{project['id']}/audio/generate")
    assert res.status_code == 409


def test_generated_audio_is_fetchable(setup):
    client, project, _, _ = setup
    client.post(f"/projects/{project['id']}/lyrics")
    client.post(f"/projects/{project['id']}/audio/generate")
    res = client.get(f"/projects/{project['id']}/audio")
    assert res.status_code == 200
    assert res.json()["source"] == "generated"


def test_generate_song_unknown_project_returns_404(setup):
    client, _, _, _ = setup
    assert client.post("/projects/nope/audio/generate").status_code == 404
