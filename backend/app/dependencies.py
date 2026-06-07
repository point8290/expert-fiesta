"""Shared FastAPI dependencies. Tests override these via ``app.dependency_overrides``."""
import os

from .adapters.audio_analysis import AudioAnalyzer, LibrosaAnalyzer
from .adapters.llm import LLMClient, OllamaClient
from .adapters.render import FFmpegRenderer, Renderer
from .comfyui.client import ComfyUIClient, ImageGenerator
from .storage import Storage
from .video.backends import LTXBackend, VideoBackend


def get_llm_client() -> LLMClient:
    return OllamaClient()


def get_storage() -> Storage:
    return Storage(os.environ.get("STORAGE_DIR", "projects"))


def get_audio_analyzer() -> AudioAnalyzer:
    return LibrosaAnalyzer()


def get_renderer() -> Renderer:
    return FFmpegRenderer()


def get_image_generator() -> ImageGenerator:
    return ComfyUIClient()


def get_video_backend() -> VideoBackend:
    return LTXBackend()
