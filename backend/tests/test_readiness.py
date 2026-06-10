"""Tests for CB-6 — readiness probing of model backends."""
from app.config import Settings
from app.services.readiness import backend_targets, check_backends


def test_no_targets_when_all_local():
    settings = Settings(llm_provider="ollama", comfyui_provider="local")
    # Local backends are co-located; readiness doesn't probe them remotely.
    assert backend_targets(settings) == {}


def test_targets_include_hosted_llm_and_runpod():
    settings = Settings(
        llm_provider="anthropic",
        llm_base_url="https://api.anthropic.test",
        comfyui_provider="runpod",
        runpod_image_endpoint="https://rp.test/img",
        runpod_video_endpoint="https://rp.test/vid",
    )
    targets = backend_targets(settings)
    assert targets["llm"] == "https://api.anthropic.test"
    assert targets["image"] == "https://rp.test/img"
    assert targets["video"] == "https://rp.test/vid"


def test_check_backends_all_ok():
    settings = Settings(
        comfyui_provider="runpod", runpod_image_endpoint="https://rp.test/img"
    )

    def probe(url: str) -> bool:
        return True

    ok, checks = check_backends(settings, probe)
    assert ok is True
    assert checks == {"image": "ok"}


def test_check_backends_reports_unreachable():
    settings = Settings(
        comfyui_provider="runpod", runpod_image_endpoint="https://rp.test/img"
    )

    def probe(url: str) -> bool:
        return False

    ok, checks = check_backends(settings, probe)
    assert ok is False
    assert checks == {"image": "unreachable"}


def test_check_backends_no_targets_is_ready():
    settings = Settings(llm_provider="ollama", comfyui_provider="local")
    ok, checks = check_backends(settings, lambda url: False)
    assert ok is True
    assert checks == {}
