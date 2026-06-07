"""LLM adapter. The pipeline talks to language models only through ``LLMClient``
so tests can inject fakes and the backend (Ollama today) stays swappable.
"""
from typing import Protocol

from ..config import get_settings


class LLMClient(Protocol):
    def complete(self, system: str, prompt: str) -> str:
        """Return the model's text completion for a system + user prompt."""
        ...


class OllamaClient:
    """Talks to a local Ollama server. Not exercised by unit tests."""

    def __init__(self, model: str | None = None, host: str | None = None):
        settings = get_settings()
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_host

    def complete(self, system: str, prompt: str) -> str:
        import httpx

        resp = httpx.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
