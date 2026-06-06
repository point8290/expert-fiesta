"""P1-S6 — Manage individual scenes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..adapters.llm import LLMClient
from ..database import get_db
from ..dependencies import get_llm_client
from ..models import Project, Scene
from ..schemas import SceneRead, SceneUpdate
from ..services.storyboard import (
    StoryboardGenerationError,
    regenerate_scene_content,
)

router = APIRouter(prefix="/scenes", tags=["scenes"])


def _get_scene_or_404(db: Session, scene_id: str) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return scene


@router.get("/{scene_id}", response_model=SceneRead)
def get_scene(scene_id: str, db: Session = Depends(get_db)):
    return _get_scene_or_404(db, scene_id)


@router.patch("/{scene_id}", response_model=SceneRead)
def update_scene(
    scene_id: str, payload: SceneUpdate, db: Session = Depends(get_db)
):
    scene = _get_scene_or_404(db, scene_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(scene, field, value)
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/regenerate-prompt", response_model=SceneRead)
def regenerate_scene_prompt(
    scene_id: str,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    scene = _get_scene_or_404(db, scene_id)
    project = db.get(Project, scene.project_id)
    try:
        content = regenerate_scene_content(project, scene, llm)
    except StoryboardGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    for field, value in content.model_dump().items():
        setattr(scene, field, value)
    db.commit()
    db.refresh(scene)
    return scene
