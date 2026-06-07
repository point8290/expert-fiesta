"""P4-S3 — Prompt versioning.

Each time a scene's generation prompts change (storyboard creation, manual edit,
or regeneration) we snapshot them as a new ``PromptVersion``. When a keyframe or
clip is generated, the scene records which prompt version produced it, so any
asset is traceable to the exact prompt behind it.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import PromptVersion, Scene

# Fields that constitute a generation prompt (a change here warrants a version).
PROMPT_FIELDS = ("keyframe_prompt", "video_prompt", "negative_prompt")


def latest_version_number(db: Session, scene_id: str) -> int:
    result = db.scalar(
        select(func.max(PromptVersion.version)).where(
            PromptVersion.scene_id == scene_id
        )
    )
    return result or 0


def record_version(db: Session, scene: Scene) -> PromptVersion:
    """Snapshot the scene's current prompts as the next version."""
    version = PromptVersion(
        scene_id=scene.id,
        version=latest_version_number(db, scene.id) + 1,
        keyframe_prompt=scene.keyframe_prompt,
        video_prompt=scene.video_prompt,
        negative_prompt=scene.negative_prompt,
    )
    db.add(version)
    return version
