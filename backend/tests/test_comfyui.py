"""Tests for P2-S1 — ComfyUI media adapter (template + injection + smoke-test)."""
import pytest

from app.comfyui.client import ComfyUIClient, MediaWorkflowError


@pytest.fixture()
def client():
    return ComfyUIClient()


def test_load_template_parses_committed_json(client):
    # AC2: workflow templates are committed to the repo and load as graphs.
    wf = client.load_template("keyframe")
    assert any(node.get("class_type") == "KSampler" for node in wf.values())


def test_build_workflow_injects_prompt_seed_resolution(client):
    # AC1: prompt/seed/resolution are injected into the workflow.
    wf = client.build_workflow(
        "keyframe",
        {
            "POSITIVE_PROMPT": "a painted rooftop at sunset",
            "NEGATIVE_PROMPT": "blurry, watermark",
            "SEED": 12345,
            "WIDTH": 1920,
            "HEIGHT": 1080,
        },
    )
    assert wf["6"]["inputs"]["text"] == "a painted rooftop at sunset"
    assert wf["7"]["inputs"]["text"] == "blurry, watermark"
    # Types are preserved: seed/width/height stay integers, not strings.
    assert wf["3"]["inputs"]["seed"] == 12345
    assert wf["5"]["inputs"]["width"] == 1920
    assert wf["5"]["inputs"]["height"] == 1080


def test_build_workflow_missing_param_raises(client):
    with pytest.raises(MediaWorkflowError):
        client.build_workflow("keyframe", {"POSITIVE_PROMPT": "x"})


def test_build_workflow_unknown_template_raises(client):
    with pytest.raises(MediaWorkflowError):
        client.build_workflow("does_not_exist", {})


def test_smoke_test_validates_all_templates(client):
    # AC3: a smoke-test validates each committed workflow loads.
    names = client.smoke_test()
    assert "keyframe" in names
    assert "character" in names
