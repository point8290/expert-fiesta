"""Registry of available video backends, keyed by the name stored on a project."""
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

DEFAULT_BACKEND = "ltx"


def build_video_backend(name: str) -> VideoBackend:
    """Instantiate the backend for ``name``; raises KeyError if unknown."""
    return VIDEO_BACKENDS[name]()


def build_registry() -> dict[str, VideoBackend]:
    return {name: cls() for name, cls in VIDEO_BACKENDS.items()}
