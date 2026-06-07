"""P4-S4 — Character consistency scoring across scenes."""
from ..adapters.consistency import ConsistencyScorer
from ..models import Character, Scene
from ..schemas import ConsistencyScoreRead


def score_scenes(
    scenes: list[Scene],
    characters: list[Character],
    scorer: ConsistencyScorer,
) -> list[ConsistencyScoreRead]:
    """Score every (scene keyframe, approved-character reference) pair."""
    refs = [
        c
        for c in characters
        if c.ref_status == "approved" and c.ref_image_path
    ]
    results: list[ConsistencyScoreRead] = []
    for scene in sorted(scenes, key=lambda s: s.number):
        if not scene.keyframe_path:
            continue
        for character in refs:
            results.append(
                ConsistencyScoreRead(
                    scene_id=scene.id,
                    character_id=character.id,
                    score=round(
                        scorer.score(character.ref_image_path, scene.keyframe_path), 4
                    ),
                )
            )
    return results
