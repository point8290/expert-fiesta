"""CB-6 — Readiness probing of remote model backends.

When the LLM and/or ComfyUI run on hosted/serverless providers, a node is only
truly "ready" once those endpoints are reachable. ``backend_targets`` derives the
set of remote endpoints from config (local backends are co-located, so they're
skipped), and ``check_backends`` probes each one through an injected callable so
the logic stays testable without real network access.
"""
from typing import Callable

from ..config import Settings

# A probe returns True if the endpoint answered, False otherwise.
ProbeFn = Callable[[str], bool]

DEFAULT_LLM_BASE = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
}


def backend_targets(settings: Settings) -> dict[str, str]:
    """Map of backend name -> base URL to probe. Local backends are omitted."""
    targets: dict[str, str] = {}

    if settings.llm_provider in ("anthropic", "openai"):
        targets["llm"] = settings.llm_base_url or DEFAULT_LLM_BASE[settings.llm_provider]

    if settings.comfyui_provider == "runpod":
        if settings.runpod_image_endpoint:
            targets["image"] = settings.runpod_image_endpoint
        if settings.runpod_video_endpoint:
            targets["video"] = settings.runpod_video_endpoint
        if settings.runpod_audio_endpoint:
            targets["audio"] = settings.runpod_audio_endpoint

    return targets


def check_backends(settings: Settings, probe: ProbeFn) -> tuple[bool, dict[str, str]]:
    """Probe every remote backend; return (all_ok, {name: "ok"|"unreachable"})."""
    checks: dict[str, str] = {}
    all_ok = True
    for name, url in backend_targets(settings).items():
        reachable = probe(url)
        checks[name] = "ok" if reachable else "unreachable"
        all_ok = all_ok and reachable
    return all_ok, checks
