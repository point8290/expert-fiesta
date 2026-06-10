"""Tests for CB-1 — hosted LLM clients + provider selection."""
import pytest

from app.adapters import llm as llm_mod
from app.adapters.llm import (
    AnthropicLLMClient,
    LLMError,
    OllamaClient,
    OpenAILLMClient,
)
from app.config import get_settings
from app.dependencies import get_llm_client


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        import httpx

        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("POST", "http://x"), response=self  # type: ignore[arg-type]
            )

    def json(self):
        return self._payload


# --- provider selection -----------------------------------------------------

@pytest.mark.parametrize(
    "provider,cls",
    [("ollama", OllamaClient), ("anthropic", AnthropicLLMClient), ("openai", OpenAILLMClient)],
)
def test_get_llm_client_selects_provider(provider, cls, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    get_settings.cache_clear()
    try:
        assert isinstance(get_llm_client(), cls)
    finally:
        get_settings.cache_clear()


# --- Anthropic --------------------------------------------------------------

def test_anthropic_builds_request_and_parses(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse({"content": [{"type": "text", "text": '{"ok": true}'}]})

    monkeypatch.setattr(llm_mod.httpx, "post", fake_post)
    client = AnthropicLLMClient(model="claude-sonnet-4-6", api_key="k")
    out = client.complete("SYS", "USER")

    assert out == '{"ok": true}'
    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"]["x-api-key"] == "k"
    assert captured["json"]["model"] == "claude-sonnet-4-6"
    assert captured["json"]["system"] == "SYS"
    assert captured["json"]["messages"][0]["content"] == "USER"


def test_anthropic_http_error_becomes_llm_error(monkeypatch):
    def fake_post(*a, **k):
        return FakeResponse({"error": "bad"}, status=401)

    monkeypatch.setattr(llm_mod.httpx, "post", fake_post)
    with pytest.raises(LLMError):
        AnthropicLLMClient(api_key="k").complete("s", "u")


# --- OpenAI -----------------------------------------------------------------

def test_openai_builds_request_and_parses(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse(
            {"choices": [{"message": {"content": '{"ok": 1}'}}]}
        )

    monkeypatch.setattr(llm_mod.httpx, "post", fake_post)
    out = OpenAILLMClient(model="gpt-4o-mini", api_key="k").complete("SYS", "USER")

    assert out == '{"ok": 1}'
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer k"
    roles = [m["role"] for m in captured["json"]["messages"]]
    assert roles == ["system", "user"]
