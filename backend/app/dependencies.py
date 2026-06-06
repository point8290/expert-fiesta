"""Shared FastAPI dependencies. Tests override these via ``app.dependency_overrides``."""
from .adapters.llm import LLMClient, OllamaClient


def get_llm_client() -> LLMClient:
    return OllamaClient()
