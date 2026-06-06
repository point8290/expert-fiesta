"""Tests for P1-S2 — Generate lyrics and music prompt."""
import json

import pytest

from app.dependencies import get_llm_client


VALID_LYRICS = {
    "title": "Wings We Leave Behind",
    "structure": ["intro", "verse 1", "chorus", "verse 2", "chorus", "outro"],
    "body": "We climbed the rooftops chasing light...\n",
    "musicPrompt": "cinematic pop rock, bittersweet, 90 bpm, soaring chorus",
    "emotionalArc": "nostalgic longing rising to hopeful release",
}


class FakeLLM:
    """Records calls and returns canned responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


@pytest.fixture()
def use_llm(client):
    """Install a FakeLLM with the given responses and return it."""

    def _install(responses):
        fake = FakeLLM(responses)
        client.app.dependency_overrides[get_llm_client] = lambda: fake
        return fake

    return _install


def _make_project(client, project_payload):
    return client.post("/projects", json=project_payload).json()


def test_generate_lyrics_returns_all_fields(client, project_payload, use_llm):
    # AC1: returns title, structure[], body, musicPrompt, emotionalArc.
    use_llm([json.dumps(VALID_LYRICS)])
    project = _make_project(client, project_payload)

    res = client.post(f"/projects/{project['id']}/lyrics")
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == VALID_LYRICS["title"]
    assert body["structure"] == VALID_LYRICS["structure"]
    assert body["body"]
    assert body["musicPrompt"]
    assert body["emotionalArc"]


def test_system_prompt_forbids_real_works(client, project_payload, use_llm):
    # AC4: the system prompt forbids real artists/songs/lyrics/melodies.
    fake = use_llm([json.dumps(VALID_LYRICS)])
    project = _make_project(client, project_payload)

    client.post(f"/projects/{project['id']}/lyrics")
    system_prompt = fake.calls[0][0].lower()
    assert "real" in system_prompt or "existing" in system_prompt
    assert "artist" in system_prompt
    # The creator's idea must reach the model.
    assert project_payload["idea"] in fake.calls[0][1]


def test_retries_on_malformed_json_then_succeeds(client, project_payload, use_llm):
    # AC3: malformed JSON triggers a bounded retry.
    fake = use_llm(["not json at all", json.dumps(VALID_LYRICS)])
    project = _make_project(client, project_payload)

    res = client.post(f"/projects/{project['id']}/lyrics")
    assert res.status_code == 201
    assert len(fake.calls) == 2


def test_persistent_failure_returns_502(client, project_payload, use_llm):
    # AC3: persistent failure -> 502.
    use_llm(["garbage", "still garbage", "nope"])
    project = _make_project(client, project_payload)

    res = client.post(f"/projects/{project['id']}/lyrics")
    assert res.status_code == 502


def test_generate_lyrics_unknown_project_returns_404(client, use_llm):
    use_llm([json.dumps(VALID_LYRICS)])
    res = client.post("/projects/nope/lyrics")
    assert res.status_code == 404


def test_lyrics_persist_and_are_refetchable(client, project_payload, use_llm):
    # AC5: generated lyrics persist and are re-fetchable via GET.
    use_llm([json.dumps(VALID_LYRICS)])
    project = _make_project(client, project_payload)

    client.post(f"/projects/{project['id']}/lyrics")
    res = client.get(f"/projects/{project['id']}/lyrics")
    assert res.status_code == 200
    assert res.json()["title"] == VALID_LYRICS["title"]


def test_get_lyrics_when_none_returns_404(client, project_payload):
    project = _make_project(client, project_payload)
    assert client.get(f"/projects/{project['id']}/lyrics").status_code == 404
