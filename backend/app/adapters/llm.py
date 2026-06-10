"""LLM adapter. The pipeline talks to language models only through ``LLMClient``
so tests can inject fakes and the backend stays swappable. CB-1 adds hosted
providers (Anthropic, OpenAI) alongside local Ollama.
"""
from typing import Protocol

import httpx

from ..config import get_settings

# Provider defaults (override via LLM_MODEL).
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


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
            raise LLMError(
                f"LLM request failed ({exc.response.status_code}); "
                f"is model '{self.model}' pulled?"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc


class AnthropicLLMClient:
    """Hosted Anthropic Messages API (default quality provider)."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        settings = get_settings()
        self.model = model or settings.llm_model or DEFAULT_ANTHROPIC_MODEL
        self.api_key = api_key or settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url or "https://api.anthropic.com").rstrip("/")

    def complete(self, system: str, prompt: str) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=get_settings().llm_timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected Anthropic response: {exc}") from exc


class OpenAILLMClient:
    """Hosted OpenAI Chat Completions API (swappable alternative)."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        settings = get_settings()
        self.model = model or settings.llm_model or DEFAULT_OPENAI_MODEL
        self.api_key = api_key or settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")

    def complete(self, system: str, prompt: str) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=get_settings().llm_timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected OpenAI response: {exc}") from exc
