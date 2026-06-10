"""Tests for CB-2 — RunPod serverless image/video backends."""
import base64
from pathlib import Path

import pytest

from app.adapters import runpod as rp
from app.adapters.runpod import (
    RunPodClient,
    RunPodError,
    RunPodImageGenerator,
    RunPodVideoBackend,
)
from app.config import get_settings


class FakeResp:
    def __init__(self, payload, status=200):
        self._p = payload
        self.status_code = status

    def raise_for_status(self):
        import httpx

        if self.status_code >= 400:
            raise httpx.HTTPStatusError("e", request=httpx.Request("GET", "http://x"), response=self)  # type: ignore[arg-type]

    def json(self):
        return self._p


# --- RunPodClient submit + poll --------------------------------------------

def test_runpod_client_submits_and_polls(monkeypatch):
    posts, gets = [], iter(
        [
            FakeResp({"status": "IN_QUEUE"}),
            FakeResp({"status": "IN_PROGRESS"}),
            FakeResp({"status": "COMPLETED", "output": {"image_base64": "QUJD"}}),
        ]
    )

    def fake_post(url, headers=None, json=None, timeout=None):
        posts.append((url, json))
        return FakeResp({"id": "job-1", "status": "IN_QUEUE"})

    monkeypatch.setattr(rp.httpx, "post", fake_post)
    monkeypatch.setattr(rp.httpx, "get", lambda url, headers=None, timeout=None: next(gets))
    monkeypatch.setattr(rp.time, "sleep", lambda *_: None)

    out = RunPodClient("https://api.runpod.ai/v2/abc", api_key="k").run({"workflow": {}})
    assert out == {"image_base64": "QUJD"}
    assert posts[0][0].endswith("/run")
    assert posts[0][1] == {"input": {"workflow": {}}}


def test_runpod_client_raises_on_failed(monkeypatch):
    monkeypatch.setattr(rp.httpx, "post", lambda *a, **k: FakeResp({"id": "j"}))
    monkeypatch.setattr(rp.httpx, "get", lambda *a, **k: FakeResp({"status": "FAILED", "error": "oom"}))
    monkeypatch.setattr(rp.time, "sleep", lambda *_: None)
    with pytest.raises(RunPodError):
        RunPodClient("https://e", api_key="k").run({})


# --- generators write the returned asset -----------------------------------

class FakeClient:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def run(self, payload):
        self.calls.append(payload)
        return self.output


class FakeComfy:
    def build_workflow(self, name, params):
        return {"graph": name}

    def smoke_test(self):
        return ["keyframe"]


def test_image_generator_writes_base64(tmp_path):
    client = FakeClient({"image_base64": base64.b64encode(b"\x89PNG").decode()})
    gen = RunPodImageGenerator(client=client, comfy=FakeComfy())
    out = tmp_path / "k.png"
    gen.generate("keyframe", {"POSITIVE_PROMPT": "x"}, str(out))
    assert out.read_bytes() == b"\x89PNG"
    assert client.calls[0]["workflow"] == {"graph": "keyframe"}


def test_video_backend_writes_base64(tmp_path):
    client = FakeClient({"image_base64": base64.b64encode(b"\x00mp4").decode()})
    backend = RunPodVideoBackend("ltx_video", client=client, comfy=FakeComfy())
    out = tmp_path / "clip.mp4"
    backend.generate("/k.png", "pan", "blur", str(out), seed=1, frames=96)
    assert out.read_bytes() == b"\x00mp4"
    assert client.calls[0]["workflow"] == {"graph": "ltx_video"}


# --- selection by provider --------------------------------------------------

def test_image_generator_selected_for_runpod(monkeypatch):
    from app.dependencies import get_image_generator

    monkeypatch.setenv("COMFYUI_PROVIDER", "runpod")
    monkeypatch.setenv("RUNPOD_IMAGE_ENDPOINT", "https://api.runpod.ai/v2/img")
    get_settings.cache_clear()
    try:
        assert isinstance(get_image_generator(), RunPodImageGenerator)
    finally:
        get_settings.cache_clear()


def test_video_registry_uses_runpod(monkeypatch):
    from app.video.registry import build_registry

    monkeypatch.setenv("COMFYUI_PROVIDER", "runpod")
    monkeypatch.setenv("RUNPOD_VIDEO_ENDPOINT", "https://api.runpod.ai/v2/vid")
    get_settings.cache_clear()
    try:
        registry = build_registry()
        assert isinstance(registry["ltx"], RunPodVideoBackend)
        assert registry["ltx"].workflow == "ltx_video"
    finally:
        get_settings.cache_clear()
