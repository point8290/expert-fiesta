"""P2-S2 — Character bible generation service.

The LLM produces character descriptions including ``identityAnchors`` — short
distinctive tokens (e.g. "yellow hoodie") that are injected verbatim into every
keyframe prompt later, the cheapest reliable lever for character consistency.
"""
import json

from pydantic import ValidationError

from ..adapters.llm import LLMClient
from ..models import Lyrics, Project
from ..schemas import CharacterContent

MAX_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "You are a character designer for an animated music video. Invent wholly "
    "original characters; do not copy real people or existing fictional "
    "characters. Respond with a single JSON object: {\"characters\": [ ... ]}. "
    "Each character has exactly these keys: name, age, face, hair, clothing, "
    "personality, identityAnchors (an array of short distinctive visual tokens "
    "such as 'yellow hoodie' or 'messy black hair')."
)


class CharacterGenerationError(RuntimeError):
    """Raised when the LLM cannot produce a valid character bible."""


def _build_prompt(project: Project, lyrics: Lyrics | None) -> str:
    lyric_block = f"Lyrics:\n{lyrics.body}\n" if lyrics else ""
    return (
        f"Design the recurring characters for this music video.\n"
        f"Idea: {project.idea}\n"
        f"Mood: {project.mood}\n"
        f"Visual style: {project.visual_style}\n"
        f"{lyric_block}"
        "Return the cast as JSON."
    )


def generate_characters(
    project: Project, lyrics: Lyrics | None, client: LLMClient
) -> list[CharacterContent]:
    prompt = _build_prompt(project, lyrics)
    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        raw = client.complete(SYSTEM_PROMPT, prompt)
        try:
            data = json.loads(raw)
            items = data["characters"] if isinstance(data, dict) else data
            chars = [CharacterContent.model_validate(item) for item in items]
            if chars:
                return chars
            last_error = ValueError("empty character list")
        except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as exc:
            last_error = exc
    raise CharacterGenerationError(
        f"LLM failed to produce a valid character bible after {MAX_ATTEMPTS} attempts"
    ) from last_error
