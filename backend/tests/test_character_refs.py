"""Tests for P2-S3 — Character reference images."""
import json
from pathlib import Path

import pytest

from app.dependencies import get_image_generator, get_llm_client, get_storage
from app.storage import Storage


CHARACTERS = {
    "characters": [
        {
            "name": "Aarav",
            "age": "10",
            "face": "round face, brown eyes",
            "hair": "messy black hair",
            "clothing": "yellow hoodie",
            "personality": "curious",
            "identityAnchors": ["yellow hoodie", "messy black hair"],
        }
    ]
}


class FakeLLM:
    def complete(self, system, prompt):
        return json.dumps(CHARACTERS)


class FakeImageGen:
    def __init__(self):
        self.calls = []

    def generate(self, workflow, params, output_path):
        self.calls.append(
            {"workflow": workflow, "params": params, "output": output_path}
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"\x89PNG")
        return output_path

    def smoke_test(self):
        return ["character", "keyframe"]


@pytest.fixture()
def setup(client, tmp_path):
    client.app.dependency_overrides[get_storage] = lambda: Storage(tmp_path)
    client.app.dependency_overrides[get_llm_client] = lambda: FakeLLM()
    gen = FakeImageGen()
    client.app.dependency_overrides[get_image_generator] = lambda: gen
    return tmp_path, gen


def _character(client, project_payload):
    project = client.post("/projects", json=project_payload).json()
    chars = client.post(f"/projects/{project['id']}/characters").json()
    return project, chars[0]


def test_generate_reference_creates_image(client, project_payload, setup):
    # AC1: one reference image per character via ComfyUI.
    tmp_path, gen = setup
    project, char = _character(client, project_payload)

    res = client.post(f"/characters/{char['id']}/reference")
    assert res.status_code == 200
    body = res.json()
    assert body["refStatus"] == "generated"
    assert body["refImagePath"]
    assert Path(body["refImagePath"]).exists()
    assert gen.calls[0]["workflow"] == "character"


def test_reference_prompt_includes_identity_anchors(client, project_payload, setup):
    _, gen = setup
    _, char = _character(client, project_payload)
    client.post(f"/characters/{char['id']}/reference")
    prompt = gen.calls[0]["params"]["POSITIVE_PROMPT"]
    assert "yellow hoodie" in prompt
    assert "messy black hair" in prompt


def test_approve_reference(client, project_payload, setup):
    # AC2: approve.
    _, char = _character(client, project_payload)
    client.post(f"/characters/{char['id']}/reference")
    res = client.post(f"/characters/{char['id']}/reference/approve")
    assert res.status_code == 200
    assert res.json()["refStatus"] == "approved"


def test_upload_reference_replaces_manually(client, project_payload, setup):
    # AC2: replace manually.
    tmp_path, _ = setup
    _, char = _character(client, project_payload)
    res = client.post(
        f"/characters/{char['id']}/reference/upload",
        files={"file": ("ref.png", b"\x89PNGdata", "image/png")},
    )
    assert res.status_code == 200
    assert res.json()["refStatus"] == "approved"
    assert Path(res.json()["refImagePath"]).exists()


def test_upload_reference_rejects_non_image(client, project_payload, setup):
    _, char = _character(client, project_payload)
    res = client.post(
        f"/characters/{char['id']}/reference/upload",
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert res.status_code == 415


def test_reference_unknown_character_returns_404(client, setup):
    assert client.post("/characters/nope/reference").status_code == 404
