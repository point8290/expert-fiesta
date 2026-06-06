"""Tests for P2-S2 — Character bible."""
import json

import pytest

from app.dependencies import get_llm_client


CHARACTERS = {
    "characters": [
        {
            "name": "Aarav",
            "age": "10",
            "face": "round face, expressive brown eyes",
            "hair": "messy black hair",
            "clothing": "yellow hoodie",
            "personality": "curious and loyal",
            "identityAnchors": [
                "yellow hoodie",
                "messy black hair",
                "round face",
                "brown eyes",
            ],
        },
        {
            "name": "Mira",
            "age": "10",
            "face": "freckled cheeks, green eyes",
            "hair": "short auburn bob",
            "clothing": "denim overalls",
            "personality": "brave dreamer",
            "identityAnchors": ["denim overalls", "auburn bob", "freckles"],
        },
    ]
}


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, system, prompt):
        return self.payload


@pytest.fixture()
def use_llm(client):
    def _install(payload):
        client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM(payload)

    return _install


def _make_project(client, project_payload):
    return client.post("/projects", json=project_payload).json()


def test_generate_characters_returns_fields(client, project_payload, use_llm):
    # AC1: characters include name/age/face/hair/clothing/personality/anchors.
    use_llm(json.dumps(CHARACTERS))
    project = _make_project(client, project_payload)

    res = client.post(f"/projects/{project['id']}/characters")
    assert res.status_code == 201
    chars = res.json()
    assert len(chars) == 2
    first = chars[0]
    assert first["name"] == "Aarav"
    assert first["identityAnchors"] == CHARACTERS["characters"][0]["identityAnchors"]
    assert first["refStatus"] == "pending"
    for field in ("age", "face", "hair", "clothing", "personality"):
        assert field in first


def test_characters_persist_and_list(client, project_payload, use_llm):
    # AC2: characters persist.
    use_llm(json.dumps(CHARACTERS))
    project = _make_project(client, project_payload)
    client.post(f"/projects/{project['id']}/characters")

    res = client.get(f"/projects/{project['id']}/characters")
    assert res.status_code == 200
    assert {c["name"] for c in res.json()} == {"Aarav", "Mira"}


def test_patch_character_edits_fields(client, project_payload, use_llm):
    # AC2: characters are editable.
    use_llm(json.dumps(CHARACTERS))
    project = _make_project(client, project_payload)
    chars = client.post(f"/projects/{project['id']}/characters").json()

    res = client.patch(
        f"/characters/{chars[0]['id']}",
        json={"clothing": "red raincoat", "identityAnchors": ["red raincoat"]},
    )
    assert res.status_code == 200
    assert res.json()["clothing"] == "red raincoat"
    assert res.json()["identityAnchors"] == ["red raincoat"]


def test_generate_replaces_existing(client, project_payload, use_llm):
    use_llm(json.dumps(CHARACTERS))
    project = _make_project(client, project_payload)
    client.post(f"/projects/{project['id']}/characters")
    client.post(f"/projects/{project['id']}/characters")
    assert len(client.get(f"/projects/{project['id']}/characters").json()) == 2


def test_generate_unknown_project_returns_404(client, use_llm):
    use_llm(json.dumps(CHARACTERS))
    assert client.post("/projects/nope/characters").status_code == 404


def test_patch_unknown_character_returns_404(client, project_payload, use_llm):
    assert client.patch("/characters/nope", json={"clothing": "x"}).status_code == 404
