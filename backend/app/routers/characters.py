"""P2-S2 character bible + P2-S3 character reference image endpoints."""
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..adapters.consistency import ConsistencyScorer
from ..adapters.llm import LLMClient
from ..comfyui.client import ImageGenerator
from ..database import get_db
from ..dependencies import (
    get_consistency_scorer,
    get_image_generator,
    get_llm_client,
    get_storage,
)
from ..models import Character, Lyrics, Project, Scene
from ..schemas import CharacterRead, CharacterUpdate, ConsistencyScoreRead
from ..services.characters import CharacterGenerationError, generate_characters
from ..services.consistency import score_scenes
from ..services.images import generate_character_reference
from ..storage import Storage

router = APIRouter(tags=["characters"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


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


@router.get(
    "/projects/{project_id}/consistency",
    response_model=list[ConsistencyScoreRead],
)
def consistency_scores(
    project_id: str,
    db: Session = Depends(get_db),
    scorer: ConsistencyScorer = Depends(get_consistency_scorer),
):
    _get_project_or_404(db, project_id)
    characters = list(
        db.scalars(select(Character).where(Character.project_id == project_id))
    )
    scenes = list(
        db.scalars(select(Scene).where(Scene.project_id == project_id))
    )
    return score_scenes(scenes, characters, scorer)


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


@router.post("/characters/{character_id}/reference", response_model=CharacterRead)
def generate_reference(
    character_id: str,
    db: Session = Depends(get_db),
    generator: ImageGenerator = Depends(get_image_generator),
    storage: Storage = Depends(get_storage),
):
    character = _get_character_or_404(db, character_id)
    project = db.get(Project, character.project_id)
    path = generate_character_reference(project, character, generator, storage)
    character.ref_image_path = path
    character.ref_status = "generated"
    db.commit()
    db.refresh(character)
    return character


@router.post(
    "/characters/{character_id}/reference/approve", response_model=CharacterRead
)
def approve_reference(character_id: str, db: Session = Depends(get_db)):
    character = _get_character_or_404(db, character_id)
    character.ref_status = "approved"
    db.commit()
    db.refresh(character)
    return character


@router.post(
    "/characters/{character_id}/reference/upload", response_model=CharacterRead
)
def upload_reference(
    character_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    character = _get_character_or_404(db, character_id)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {file.content_type}",
        )
    path = storage.save_upload(
        character.project_id, "characters", f"{character_id}{_suffix(file.filename)}", file.file
    )
    character.ref_image_path = str(path)
    character.ref_status = "approved"
    db.commit()
    db.refresh(character)
    return character


def _suffix(filename: str | None) -> str:
    if filename and "." in filename:
        return filename[filename.rfind(".") :]
    return ".png"
