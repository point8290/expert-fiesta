"""Tests for CB-4 — video backend fallback + circuit breaker."""
from pathlib import Path

from app.config import get_settings
from app.video.fallback import CircuitBreaker, FallbackVideoBackend


class Recording:
    def __init__(self, name, fail=False):
        self.name = name
        self.workflow = name
        self.fail = fail
        self.calls = 0

    def generate(self, keyframe_path, video_prompt, negative_prompt, output_path, *, seed=None, frames=120):
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self.name} boom")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(self.name.encode())
        return output_path


def _gen(backend, out):
    return backend.generate("/k.png", "p", "n", str(out))


def test_uses_primary_on_success(tmp_path):
    primary, fallback = Recording("primary"), Recording("fallback")
    out = tmp_path / "c.mp4"
    _gen(FallbackVideoBackend(primary, fallback), out)
    assert out.read_bytes() == b"primary"
    assert fallback.calls == 0


def test_falls_back_on_primary_failure(tmp_path):
    primary, fallback = Recording("primary", fail=True), Recording("fallback")
    out = tmp_path / "c.mp4"
    _gen(FallbackVideoBackend(primary, fallback), out)
    assert out.read_bytes() == b"fallback"
    assert primary.calls == 1 and fallback.calls == 1


def test_circuit_opens_after_threshold(tmp_path):
    primary = Recording("primary", fail=True)
    fallback = Recording("fallback")
    backend = FallbackVideoBackend(primary, fallback, breaker=CircuitBreaker(threshold=2, cooldown=60))

    _gen(backend, tmp_path / "1.mp4")  # fail -> fallback (failure 1)
    _gen(backend, tmp_path / "2.mp4")  # fail -> fallback (failure 2 -> opens)
    primary.fail = False               # primary would work now...
    _gen(backend, tmp_path / "3.mp4")  # ...but circuit is open -> straight to fallback

    assert primary.calls == 2  # not called on the 3rd request
    assert fallback.calls == 3


def test_registry_wraps_runpod_with_fallback(monkeypatch):
    from app.adapters.runpod import RunPodVideoBackend
    from app.video.registry import build_registry

    monkeypatch.setenv("COMFYUI_PROVIDER", "runpod")
    monkeypatch.setenv("RUNPOD_VIDEO_ENDPOINT", "https://api.runpod.ai/v2/vid")
    monkeypatch.setenv("CLOUD_VIDEO_URL", "https://cloud.example.com")
    get_settings.cache_clear()
    try:
        registry = build_registry()
        assert isinstance(registry["ltx"], FallbackVideoBackend)
        assert isinstance(registry["ltx"].primary, RunPodVideoBackend)
    finally:
        get_settings.cache_clear()
