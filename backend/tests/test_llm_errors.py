"""Regression for the Ollama-down case: LLM transport errors -> 502, not 500."""
import json

import pytest

from app.adapters.llm import LLMError
from app.dependencies import get_llm_client


class FailingLLM:
    def complete(self, system, prompt):
        raise LLMError("model 'llama3.1' not pulled (404)")


@pytest.fixture()
def failing_llm(client):
    client.app.dependency_overrides[get_llm_client] = lambda: FailingLLM()


def _project(client, project_payload):
    return client.post("/projects", json=project_payload).json()


def test_lyrics_llm_failure_returns_502(client, project_payload, failing_llm):
    project = _project(client, project_payload)
    res = client.post(f"/projects/{project['id']}/lyrics")
    assert res.status_code == 502
    assert "model" in res.json()["detail"].lower()


def test_characters_llm_failure_returns_502(client, project_payload, failing_llm):
    project = _project(client, project_payload)
    res = client.post(f"/projects/{project['id']}/characters")
    assert res.status_code == 502


def test_storyboard_llm_failure_returns_502(client, project_payload, failing_llm):
    project = _project(client, project_payload)
    res = client.post(f"/projects/{project['id']}/storyboard")
    assert res.status_code == 502
