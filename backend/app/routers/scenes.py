"""P1-S6 — Manage individual scenes (owner-scoped, P5-S2)."""
import os

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters.llm import LLMClient
from ..comfyui.client import ImageGenerator
from ..config import get_settings
from ..database import get_db
from ..dependencies import (
    get_current_user,
    get_image_generator,
    get_llm_client,
    get_storage,
    get_video_registry,
)
from ..models import Character, Project, PromptVersion, Scene, User
from ..ownership import require_scene
from ..schemas import JobRead, PromptVersionRead, SceneRead, SceneUpdate
from ..services.clips import BackendError, generate_clip_for_scene, resolve_backend
from ..services.images import generate_scene_keyframe
from ..services.jobs import create_job, execute_job
from ..services.quota import assert_active_job_quota
from ..services.prompt_versions import (
    PROMPT_FIELDS,
    latest_version_number,
    record_version,
)
from ..services.storyboard import (
    StoryboardGenerationError,
    regenerate_scene_content,
)
from ..storage import Storage
from ..uploads import enforce_upload_size
from ..video.backends import VideoBackend

router = APIRouter(prefix="/scenes", tags=["scenes"])

ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/x-msvideo",
}
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _image_suffix(filename: str | None) -> str:
    if filename and "." in filename:
        return filename[filename.rfind(".") :]
    return ".png"


def owned_scene(
    scene_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scene:
    """Resolve a scene the current user owns (404 otherwise)."""
    return require_scene(db, scene_id, current_user)


@router.get("/{scene_id}", response_model=SceneRead)
def get_scene(scene: Scene = Depends(owned_scene)):
    return scene


@router.get("/{scene_id}/keyframe/file")
def serve_keyframe(scene: Scene = Depends(owned_scene)):
    if not scene.keyframe_path or not os.path.exists(scene.keyframe_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Keyframe not found")
    return FileResponse(scene.keyframe_path)


@router.get("/{scene_id}/clip/file")
def serve_clip(scene: Scene = Depends(owned_scene)):
    if not scene.clip_path or not os.path.exists(scene.clip_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Clip not found")
    return FileResponse(scene.clip_path)


@router.patch("/{scene_id}", response_model=SceneRead)
def update_scene(
    payload: SceneUpdate,
    scene: Scene = Depends(owned_scene),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True)
    prompt_changed = any(
        field in changes and changes[field] != getattr(scene, field)
        for field in PROMPT_FIELDS
    )
    for field, value in changes.items():
        setattr(scene, field, value)
    if prompt_changed:
        record_version(db, scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.get("/{scene_id}/prompt-versions", response_model=list[PromptVersionRead])
def list_prompt_versions(
    scene: Scene = Depends(owned_scene), db: Session = Depends(get_db)
):
    stmt = (
        select(PromptVersion)
        .where(PromptVersion.scene_id == scene.id)
        .order_by(PromptVersion.version)
    )
    return list(db.scalars(stmt))


@router.post("/{scene_id}/regenerate-prompt", response_model=SceneRead)
def regenerate_scene_prompt(
    scene: Scene = Depends(owned_scene),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    project = db.get(Project, scene.project_id)
    try:
        content = regenerate_scene_content(project, scene, llm)
    except StoryboardGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    for field, value in content.model_dump().items():
        setattr(scene, field, value)
    record_version(db, scene)
    db.commit()
    db.refresh(scene)
    return scene


@router.post(
    "/{scene_id}/clip", response_model=SceneRead, status_code=status.HTTP_201_CREATED
)
def upload_clip(
    file: UploadFile = File(...),
    scene: Scene = Depends(owned_scene),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    enforce_upload_size(file)
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video type: {file.content_type}",
        )
    path = storage.save_upload(
        scene.project_id, f"scenes/{scene.id}", file.filename, file.file
    )
    scene.clip_path = str(path)
    scene.clip_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/finalize", response_model=SceneRead)
def finalize_scene(scene: Scene = Depends(owned_scene), db: Session = Depends(get_db)):
    scene.clip_status = "final"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/keyframe", response_model=SceneRead)
def generate_keyframe(
    scene: Scene = Depends(owned_scene),
    db: Session = Depends(get_db),
    generator: ImageGenerator = Depends(get_image_generator),
    storage: Storage = Depends(get_storage),
):
    scene.keyframe_prompt_version = latest_version_number(db, scene.id)
    # CB-3: run on the worker in async mode; otherwise inline.
    if get_settings().async_jobs:
        scene.keyframe_status = "generating"
        create_job(db, "keyframe", scene.project_id, scene_id=scene.id, target_id=scene.id)
        db.commit()
        db.refresh(scene)
        return scene

    project = db.get(Project, scene.project_id)
    characters = list(
        db.scalars(select(Character).where(Character.project_id == scene.project_id))
    )
    path = generate_scene_keyframe(project, scene, characters, generator, storage)
    scene.keyframe_path = path
    scene.keyframe_status = "generated"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/keyframe/approve", response_model=SceneRead)
def approve_keyframe(scene: Scene = Depends(owned_scene), db: Session = Depends(get_db)):
    scene.keyframe_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/clip/generate", response_model=JobRead)
def generate_clip(
    scene: Scene = Depends(owned_scene),
    db: Session = Depends(get_db),
    registry: dict[str, VideoBackend] = Depends(get_video_registry),
    storage: Storage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    if scene.keyframe_status != "approved" or not scene.keyframe_path:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Scene needs an approved keyframe before generating a clip",
        )
    assert_active_job_quota(db, current_user)
    project = db.get(Project, scene.project_id)
    try:
        backend = resolve_backend(registry, project, scene)
    except BackendError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # PR0-5: enqueue for the worker in async mode; otherwise run inline.
    if get_settings().async_jobs:
        return create_job(db, "clip", scene.project_id, scene_id=scene.id)

    return execute_job(
        db,
        "clip",
        scene.project_id,
        lambda progress: generate_clip_for_scene(db, scene, backend, storage),
        scene_id=scene.id,
    )


@router.post("/{scene_id}/clip/approve", response_model=SceneRead)
def approve_clip(scene: Scene = Depends(owned_scene), db: Session = Depends(get_db)):
    scene.clip_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/keyframe/upload", response_model=SceneRead)
def upload_keyframe(
    file: UploadFile = File(...),
    scene: Scene = Depends(owned_scene),
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
        scene.project_id,
        f"scenes/{scene.id}",
        f"keyframe{_image_suffix(file.filename)}",
        file.file,
    )
    scene.keyframe_path = str(path)
    scene.keyframe_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene
