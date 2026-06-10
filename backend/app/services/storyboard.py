"""P1-S5 — Storyboard generation service.

The LLM provides *descriptive* scene content only. Timing is computed here from
the audio (duration, beats, sections) and never trusted from the model: scene
boundaries are spread evenly then snapped to real beats, which keeps cuts on the
music. This is the keystone of accurate audio-video sync.
"""
import json

from pydantic import ValidationError

from ..adapters.llm import LLMClient, LLMError
from ..models import Audio, Lyrics, Project, Scene
from ..schemas import SceneContent

MAX_ATTEMPTS = 3
SCENE_TARGET_SECONDS = 5
SCENE_COUNT_MIN = 8
SCENE_COUNT_MAX = 12

SYSTEM_PROMPT = (
    "You are a music-video storyboard artist. Produce wholly original visuals; "
    "do not imitate real, existing music videos, films, or artists. "
    "Respond with a single JSON object: {\"scenes\": [ ... ]}. Each scene is an "
    "object with exactly these keys: visualDescription, cameraInstruction, "
    "motionInstruction, keyframePrompt, videoPrompt, negativePrompt. Do not "
    "include timing — timing is assigned by the system."
)


class StoryboardGenerationError(RuntimeError):
    """Raised when the LLM cannot produce a valid storyboard within MAX_ATTEMPTS."""


def _clamp_count(total: float) -> int:
    raw = round(total / SCENE_TARGET_SECONDS)
    return max(SCENE_COUNT_MIN, min(SCENE_COUNT_MAX, raw))


def _build_prompt(project: Project, lyrics: Lyrics | None, count: int) -> str:
    lyric_block = f"Lyrics:\n{lyrics.body}\n" if lyrics else ""
    return (
        f"Create a {count}-scene storyboard for an animated music video.\n"
        f"Idea: {project.idea}\n"
        f"Genre: {project.genre}\n"
        f"Mood: {project.mood}\n"
        f"Visual style: {project.visual_style}\n"
        f"{lyric_block}"
        f"Return exactly {count} scenes."
    )


def _parse_scenes(raw: str) -> list[SceneContent]:
    data = json.loads(raw)
    items = data["scenes"] if isinstance(data, dict) else data
    return [SceneContent.model_validate(item) for item in items]


def _generate_contents(client: LLMClient, prompt: str) -> list[SceneContent]:
    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            contents = _parse_scenes(client.complete(SYSTEM_PROMPT, prompt))
            if contents:
                return contents
            last_error = ValueError("empty scene list")
        except (json.JSONDecodeError, KeyError, TypeError, ValidationError, LLMError) as exc:
            last_error = exc
    raise StoryboardGenerationError(
        f"Storyboard generation failed: {last_error}"
    ) from last_error


REGEN_SYSTEM_PROMPT = (
    "You are a music-video storyboard artist. Rewrite a single scene as original "
    "content. Respond with one JSON object with exactly these keys: "
    "visualDescription, cameraInstruction, motionInstruction, keyframePrompt, "
    "videoPrompt, negativePrompt."
)


def regenerate_scene_content(
    project: Project, scene: Scene, client: LLMClient
) -> SceneContent:
    """Re-generate just the descriptive content of one scene; timing is kept."""
    prompt = (
        f"Visual style: {project.visual_style}\nMood: {project.mood}\n"
        f"Section: {scene.section_name}\n"
        f"Current description: {scene.visual_description}\n"
        "Produce a fresh take on this scene."
    )
    last_error: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        try:
            return SceneContent.model_validate(json.loads(client.complete(REGEN_SYSTEM_PROMPT, prompt)))
        except (json.JSONDecodeError, ValidationError, LLMError) as exc:
            last_error = exc
    raise StoryboardGenerationError(
        f"Scene regeneration failed: {last_error}"
    ) from last_error


def _snap(t: float, beats: list[float] | None) -> float:
    if not beats:
        return t
    return min(beats, key=lambda b: abs(b - t))


def _section_for(t: float, sections: list | None) -> str:
    if not sections:
        return ""
    for s in sections:
        if s["start"] <= t < s["end"]:
            return s["name"]
    return sections[-1]["name"]


def _boundaries(n: int, total: float, beats: list[float] | None) -> list[float]:
    step = total / n
    edges = [i * step for i in range(n + 1)]
    if beats:
        for i in range(1, n):
            edges[i] = _snap(edges[i], beats)
    edges[0] = 0.0
    edges[-1] = total
    # Guarantee strictly increasing edges even if two snapped to the same beat.
    for i in range(1, n + 1):
        if edges[i] <= edges[i - 1]:
            edges[i] = edges[i - 1] + step
    edges[-1] = total
    return edges


def generate_storyboard(
    project: Project,
    lyrics: Lyrics | None,
    audio: Audio | None,
    client: LLMClient,
) -> list[Scene]:
    total = (
        audio.duration_seconds
        if audio and audio.duration_seconds
        else float(project.target_duration)
    )
    count = _clamp_count(total)

    contents = _generate_contents(client, _build_prompt(project, lyrics, count))
    contents = contents[:count]

    beats = audio.beats if audio else None
    sections = audio.sections if audio else None
    edges = _boundaries(len(contents), total, beats)

    scenes: list[Scene] = []
    for i, content in enumerate(contents):
        start, end = round(edges[i], 3), round(edges[i + 1], 3)
        scenes.append(
            Scene(
                project_id=project.id,
                number=i + 1,
                start_time=start,
                end_time=end,
                duration_seconds=round(end - start, 3),
                section_name=_section_for(start, sections),
                **content.model_dump(),
            )
        )
    return scenes
