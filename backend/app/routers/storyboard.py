"""P1-S5 — Storyboard generation endpoints (+ P4-S6 beat-synced cut suggestions)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..adapters.llm import LLMClient
from ..database import get_db
from ..dependencies import get_llm_client
from ..models import Audio, Lyrics, Project, Scene
from ..schemas import BeatCutsRead, SceneRead
from ..services.beat_cuts import suggest_cuts
from ..services.prompt_versions import record_version
from ..services.storyboard import StoryboardGenerationError, generate_storyboard

router = APIRouter(tags=["storyboard"])


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post(
    "/projects/{project_id}/storyboard",
    response_model=list[SceneRead],
    status_code=status.HTTP_201_CREATED,
)
def create_storyboard(
    project_id: str,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    project = _get_project_or_404(db, project_id)
    lyrics = db.get(Lyrics, project_id)
    audio = db.get(Audio, project_id)

    try:
        scenes = generate_storyboard(project, lyrics, audio, llm)
    except StoryboardGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    # Regenerating replaces the existing storyboard.
    db.execute(delete(Scene).where(Scene.project_id == project_id))
    db.add_all(scenes)
    db.flush()
    for scene in scenes:
        record_version(db, scene)  # initial v1 snapshot per scene
    db.commit()
    for scene in scenes:
        db.refresh(scene)
    return scenes


@router.get("/projects/{project_id}/scenes", response_model=list[SceneRead])
def list_scenes(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    stmt = select(Scene).where(Scene.project_id == project_id).order_by(Scene.number)
    return list(db.scalars(stmt))


@router.get("/projects/{project_id}/beat-cuts", response_model=BeatCutsRead)
def beat_cuts(
    project_id: str,
    segments: int = Query(8, ge=1),
    db: Session = Depends(get_db),
):
    _get_project_or_404(db, project_id)
    audio = db.get(Audio, project_id)
    if audio is None or not audio.beats or not audio.duration_seconds:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="No analyzed audio with beats"
        )
    return BeatCutsRead(
        cuts=suggest_cuts(audio.beats, audio.duration_seconds, segments)
    )
