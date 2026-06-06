"""Shared FastAPI dependencies. Tests override these via ``app.dependency_overrides``."""
import os

from .adapters.audio_analysis import AudioAnalyzer, LibrosaAnalyzer
from .adapters.llm import LLMClient, OllamaClient
from .storage import Storage


def get_llm_client() -> LLMClient:
    return OllamaClient()


def get_storage() -> Storage:
    return Storage(os.environ.get("STORAGE_DIR", "projects"))


def get_audio_analyzer() -> AudioAnalyzer:
    return LibrosaAnalyzer()
