"""Image-generation prompt building + ComfyUI invocation (P2-S3 / P2-S4).

Shared by character references and scene keyframes. Identity-anchor tokens are
injected verbatim into prompts so characters stay visually consistent.
"""
import random

from ..comfyui.client import ImageGenerator
from ..models import Character, Project, Scene
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


def keyframe_params(
    project: Project,
    scene: Scene,
    characters: list[Character],
    seed: int,
    reference_image: str | None = None,
) -> dict:
    # P2-S5: inject every character's identity anchors verbatim for consistency.
    anchors = ", ".join(
        anchor
        for character in characters
        for anchor in (character.identity_anchors or [])
    )
    positive = ", ".join(
        part
        for part in [project.visual_style, scene.keyframe_prompt, anchors]
        if part
    )
    width, height = ASPECT_RESOLUTIONS.get(project.aspect_ratio, (1920, 1080))
    params = {
        "POSITIVE_PROMPT": positive,
        "NEGATIVE_PROMPT": scene.negative_prompt or DEFAULT_NEGATIVE,
        "SEED": seed,
        "WIDTH": width,
        "HEIGHT": height,
    }
    if reference_image:
        # P2-S5 AC2: IP-Adapter consumes the approved character reference image.
        params["REFERENCE_IMAGE"] = reference_image
    return params


def _approved_reference(characters: list[Character]) -> str | None:
    for character in characters:
        if character.ref_status == "approved" and character.ref_image_path:
            return character.ref_image_path
    return None


def generate_scene_keyframe(
    project: Project,
    scene: Scene,
    characters: list[Character],
    generator: ImageGenerator,
    storage: Storage,
    seed: int | None = None,
) -> str:
    seed = _random_seed() if seed is None else seed
    output = (
        storage.project_dir(project.id, "scenes", scene.id) / "keyframe.png"
    )
    reference = _approved_reference(characters)
    workflow = "keyframe_ipadapter" if reference else "keyframe"
    params = keyframe_params(project, scene, characters, seed, reference)
    generator.generate(workflow, params, str(output))
    return str(output)
