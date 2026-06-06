"""Image-generation prompt building + ComfyUI invocation (P2-S3 / P2-S4).

Shared by character references and scene keyframes. Identity-anchor tokens are
injected verbatim into prompts so characters stay visually consistent.
"""
import random

from ..comfyui.client import ImageGenerator
from ..models import Character, Project
from ..storage import Storage

DEFAULT_NEGATIVE = "deformed, extra limbs, text, watermark, low quality, blurry"
ASPECT_RESOLUTIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1024, 1024),
    "4:3": (1440, 1080),
}


def _random_seed() -> int:
    return random.randint(0, 2**31 - 1)


def character_reference_params(
    project: Project, character: Character, seed: int
) -> dict:
    anchors = ", ".join(character.identity_anchors or [])
    positive = ", ".join(
        part
        for part in [
            project.visual_style,
            "character reference sheet, full body and face",
            character.name,
            character.face,
            character.hair,
            character.clothing,
            anchors,
        ]
        if part
    )
    return {
        "POSITIVE_PROMPT": positive,
        "NEGATIVE_PROMPT": DEFAULT_NEGATIVE,
        "SEED": seed,
        "WIDTH": 1024,
        "HEIGHT": 1024,
    }


def generate_character_reference(
    project: Project,
    character: Character,
    generator: ImageGenerator,
    storage: Storage,
    seed: int | None = None,
) -> str:
    seed = _random_seed() if seed is None else seed
    output = storage.project_dir(project.id, "characters") / f"{character.id}.png"
    params = character_reference_params(project, character, seed)
    generator.generate("character", params, str(output))
    return str(output)
