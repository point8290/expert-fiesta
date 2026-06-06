"""Tests for P3-S1 — VideoBackend interface + LTX-Video."""
from app.comfyui.client import ComfyUIClient
from app.video.backends import LTXBackend


def test_ltx_workflow_template_is_committed():
    # AC2: LTX implements via a committed ComfyUI workflow.
    assert "ltx_video" in ComfyUIClient().smoke_test()


def test_ltx_params_include_keyframe_and_prompts():
    # AC1: contract takes keyframe + video prompt + negative prompt.
    backend = LTXBackend()
    params = backend.params(
        keyframe_path="/p/keyframe.png",
        video_prompt="slow push-in, birds drifting",
        negative_prompt="flicker, watermark",
        seed=7,
        frames=120,
        width=768,
        height=512,
    )
    assert params["KEYFRAME_IMAGE"] == "/p/keyframe.png"
    assert params["POSITIVE_PROMPT"] == "slow push-in, birds drifting"
    assert params["NEGATIVE_PROMPT"] == "flicker, watermark"
    assert params["SEED"] == 7
    assert params["FRAMES"] == 120


def test_ltx_params_default_negative_prompt():
    backend = LTXBackend()
    params = backend.params(
        keyframe_path="/p/k.png",
        video_prompt="pan",
        negative_prompt="",
        seed=1,
        frames=120,
        width=768,
        height=512,
    )
    assert params["NEGATIVE_PROMPT"]  # falls back to a default


def test_ltx_workflow_injects_into_template():
    backend = LTXBackend()
    wf = backend.comfy.build_workflow(
        backend.workflow,
        backend.params(
            keyframe_path="/p/k.png",
            video_prompt="pan",
            negative_prompt="blur",
            seed=42,
            frames=96,
            width=768,
            height=512,
        ),
    )
    # The injected seed is an int, not a leftover placeholder string.
    seeds = [
        node["inputs"]["seed"]
        for node in wf.values()
        if "seed" in node.get("inputs", {})
    ]
    assert 42 in seeds
