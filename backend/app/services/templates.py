"""P5-S1 — Project templates.

Named starting configurations a creator can spin a new project from, pre-filling
genre/mood/visual style/aspect ratio/duration/video backend/transition.
"""
from ..schemas import ProjectTemplateRead

PROJECT_TEMPLATES: list[ProjectTemplateRead] = [
    ProjectTemplateRead(
        id="cinematic_pop_rock",
        name="Cinematic Pop-Rock (16:9)",
        genre="cinematic pop rock",
        mood="bittersweet and uplifting",
        visual_style="2D hand-painted animation",
        aspect_ratio="16:9",
        target_duration=60,
        video_backend="ltx",
        transition="crossfade",
    ),
    ProjectTemplateRead(
        id="vertical_tiktok",
        name="Vertical Short (9:16)",
        genre="upbeat electronic pop",
        mood="energetic and playful",
        visual_style="bold flat-color animation",
        aspect_ratio="9:16",
        target_duration=30,
        video_backend="ltx",
        transition="cut",
    ),
    ProjectTemplateRead(
        id="lofi_square",
        name="Lo-fi Loop (1:1)",
        genre="lo-fi hip hop",
        mood="calm and nostalgic",
        visual_style="cozy anime illustration",
        aspect_ratio="1:1",
        target_duration=45,
        video_backend="wan",
        transition="crossfade",
    ),
]

_BY_ID = {t.id: t for t in PROJECT_TEMPLATES}


def list_templates() -> list[ProjectTemplateRead]:
    return PROJECT_TEMPLATES


def get_template(template_id: str) -> ProjectTemplateRead | None:
    return _BY_ID.get(template_id)
