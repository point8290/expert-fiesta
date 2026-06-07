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
    get_current_user,
    get_image_generator,
    get_llm_client,
    get_storage,
)
from ..models import Character, Lyrics, Project, Scene, User
from ..ownership import require_character, require_project
from ..schemas import CharacterRead, CharacterUpdate, ConsistencyScoreRead
from ..services.characters import CharacterGenerationError, generate_characters
from ..services.consistency import score_scenes
from ..services.images import generate_character_reference
from ..storage import Storage
from ..uploads import enforce_upload_size

router = APIRouter(tags=["characters"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def owned_character(
    character_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Character:
    return require_character(db, character_id, current_user)


@router.post(
    "/projects/{project_id}/characters",
    response_model=list[CharacterRead],
    status_code=status.HTTP_201_CREATED,
)
def create_characters(
    project_id: str,
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)
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
def list_characters(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
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
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
    characters = list(
        db.scalars(select(Character).where(Character.project_id == project_id))
    )
    scenes = list(
        db.scalars(select(Scene).where(Scene.project_id == project_id))
    )
    return score_scenes(scenes, characters, scorer)


@router.patch("/characters/{character_id}", response_model=CharacterRead)
def update_character(
    payload: CharacterUpdate,
    character: Character = Depends(owned_character),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(character, field, value)
    db.commit()
    db.refresh(character)
    return character


@router.post("/characters/{character_id}/reference", response_model=CharacterRead)
def generate_reference(
    character: Character = Depends(owned_character),
    db: Session = Depends(get_db),
    generator: ImageGenerator = Depends(get_image_generator),
    storage: Storage = Depends(get_storage),
):
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
def approve_reference(
    character: Character = Depends(owned_character), db: Session = Depends(get_db)
):
    character.ref_status = "approved"
    db.commit()
    db.refresh(character)
    return character


@router.post(
    "/characters/{character_id}/reference/upload", response_model=CharacterRead
)
def upload_reference(
    file: UploadFile = File(...),
    character: Character = Depends(owned_character),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    enforce_upload_size(file)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {file.content_type}",
        )
    path = storage.save_upload(
        character.project_id, "characters", f"{character.id}{_suffix(file.filename)}", file.file
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
