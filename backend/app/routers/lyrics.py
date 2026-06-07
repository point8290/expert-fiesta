"""P1-S2 — Lyrics generation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..adapters.llm import LLMClient
from ..database import get_db
from ..dependencies import get_current_user, get_llm_client
from ..models import Lyrics, User
from ..ownership import require_project
from ..schemas import LyricsData
from ..services.lyrics import LyricsGenerationError, generate_lyrics

router = APIRouter(prefix="/projects/{project_id}/lyrics", tags=["lyrics"])


@router.post("", response_model=LyricsData, status_code=status.HTTP_201_CREATED)
def create_lyrics(
    project_id: str,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)
    try:
        data = generate_lyrics(project, llm)
    except LyricsGenerationError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    row = db.merge(
        Lyrics(
            project_id=project_id,
            title=data.title,
            structure=data.structure,
            body=data.body,
            music_prompt=data.music_prompt,
            emotional_arc=data.emotional_arc,
        )
    )
    db.commit()
    return LyricsData.model_validate(row)


@router.get("", response_model=LyricsData)
def get_lyrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
    row = db.get(Lyrics, project_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lyrics not found")
    return LyricsData.model_validate(row)
