"""Registry of available video backends, keyed by the name stored on a project."""
from ..config import get_settings
from .backends import (
    CloudVideoBackend,
    HunyuanBackend,
    LTXBackend,
    VideoBackend,
    WanBackend,
)

VIDEO_BACKENDS: dict[str, type] = {
    "ltx": LTXBackend,
    "wan": WanBackend,
    "hunyuan": HunyuanBackend,
    "cloud": CloudVideoBackend,
}

# Local model name -> the ComfyUI workflow it runs (used for the RunPod variant).
_RUNPOD_WORKFLOWS = {
    "ltx": "ltx_video",
    "wan": "wan_video",
    "hunyuan": "hunyuan_video",
}

DEFAULT_BACKEND = "ltx"


def build_video_backend(name: str) -> VideoBackend:
    """Instantiate the backend for ``name``; raises KeyError if unknown."""
    return VIDEO_BACKENDS[name]()


def build_registry() -> dict[str, VideoBackend]:
    if get_settings().comfyui_provider.lower() == "runpod":
        # CB-2: the local ComfyUI backends run on RunPod Serverless instead.
        from ..adapters.runpod import RunPodVideoBackend

        registry: dict[str, VideoBackend] = {
            name: RunPodVideoBackend(workflow)
            for name, workflow in _RUNPOD_WORKFLOWS.items()
        }
        registry["cloud"] = CloudVideoBackend()
        return registry
    return {name: cls() for name, cls in VIDEO_BACKENDS.items()}
