"""LLM adapter. The pipeline talks to language models only through ``LLMClient``
so tests can inject fakes and the backend (Ollama today) stays swappable.
"""
from typing import Protocol

from ..config import get_settings


class LLMError(RuntimeError):
    """Raised when the LLM backend is unreachable, errors, or times out."""


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

        try:
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
                timeout=get_settings().llm_timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except httpx.HTTPStatusError as exc:
            # 404 here usually means the model isn't pulled in Ollama.
            raise LLMError(
                f"LLM request failed ({exc.response.status_code}); "
                f"is model '{self.model}' pulled?"
            ) from exc
        except httpx.HTTPError as exc:  # timeouts, connection errors
            raise LLMError(f"LLM request failed: {exc}") from exc

