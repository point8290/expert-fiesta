"""P2-S2 — Character bible endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..adapters.llm import LLMClient
from ..database import get_db
from ..dependencies import get_llm_client
from ..models import Character, Lyrics, Project
from ..schemas import CharacterRead, CharacterUpdate
from ..services.characters import CharacterGenerationError, generate_characters

router = APIRouter(tags=["characters"])


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_character_or_404(db: Session, character_id: str) -> Character:
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Character not found")
    return character


@router.post(
    "/projects/{project_id}/characters",
    response_model=list[CharacterRead],
    status_code=status.HTTP_201_CREATED,
)
def create_characters(
    project_id: str,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    project = _get_project_or_404(db, project_id)
    lyrics = db.get(Lyrics, project_id)
    try:
        contents = generate_characters(project, lyrics, llm)
    except CharacterGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db.execute(delete(Character).where(Character.project_id == project_id))
    characters = [
        Character(project_id=project_id, **c.model_dump()) for c in contents
    ]
    db.add_all(characters)
    db.commit()
    for character in characters:
        db.refresh(character)
    return characters


@router.get(
    "/projects/{project_id}/characters", response_model=list[CharacterRead]
)
def list_characters(project_id: str, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    stmt = select(Character).where(Character.project_id == project_id)
    return list(db.scalars(stmt))


@router.patch("/characters/{character_id}", response_model=CharacterRead)
def update_character(
    character_id: str, payload: CharacterUpdate, db: Session = Depends(get_db)
):
    character = _get_character_or_404(db, character_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return character
