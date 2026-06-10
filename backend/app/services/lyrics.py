"""P1-S2 — Lyrics generation service.

Builds the prompts, calls the LLM through the adapter, and validates/retries the
JSON. Parsing and retry live here (not in the adapter) so the originality
constraint and bounded-retry behaviour are unit-testable with a fake client.
"""
import json

from pydantic import ValidationError

from ..adapters.llm import LLMClient, LLMError
from ..models import Project
from ..schemas import LyricsData

MAX_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "You are a songwriting assistant. Write original lyrics only. "
    "Do NOT copy, quote, or imitate real, existing artists, songs, lyrics, "
    "melodies, or music videos. Everything you produce must be wholly original. "
    "Respond with a single JSON object and nothing else, using exactly these "
    "keys: title (string), structure (array of section names), body (string of "
    "the full lyrics), musicPrompt (string describing the music to generate), "
    "emotionalArc (string describing the emotional progression)."
)


class LyricsGenerationError(RuntimeError):
    """Raised when the LLM cannot produce valid lyrics within MAX_ATTEMPTS."""


def build_user_prompt(project: Project) -> str:
    return (
        f"Song idea: {project.idea}\n"
        f"Genre: {project.genre}\n"
        f"Mood: {project.mood}\n"
        f"Visual style: {project.visual_style}\n"
        f"Target duration (seconds): {project.target_duration}\n"
        "Write original lyrics that fit this brief."
    )


def generate_lyrics(project: Project, client: LLMClient) -> LyricsData:
    user_prompt = build_user_prompt(project)
    last_error: Exception | None = None

    for _ in range(MAX_ATTEMPTS):
        try:
            raw = client.complete(SYSTEM_PROMPT, user_prompt)
            return LyricsData.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, LLMError) as exc:
            last_error = exc

    raise LyricsGenerationError(
        f"Lyrics generation failed: {last_error}"
    ) from last_error
