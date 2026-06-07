"""P1-S6 — Manage individual scenes."""
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from sqlalchemy import select

from ..adapters.llm import LLMClient
from ..comfyui.client import ImageGenerator
from ..database import get_db
from ..dependencies import (
    get_image_generator,
    get_llm_client,
    get_storage,
    get_video_backend,
)
from ..models import Character, Project, Scene
from ..schemas import JobRead, SceneRead, SceneUpdate
from ..services.images import generate_scene_keyframe
from ..services.jobs import execute_job
from ..services.storyboard import (
    StoryboardGenerationError,
    regenerate_scene_content,
)
from ..storage import Storage
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


@router.post(
    "/{scene_id}/clip", response_model=SceneRead, status_code=status.HTTP_201_CREATED
)
def upload_clip(
    scene_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    scene = _get_scene_or_404(db, scene_id)
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video type: {file.content_type}",
        )
    path = storage.save_upload(
        scene.project_id, f"scenes/{scene_id}", file.filename, file.file
    )
    scene.clip_path = str(path)
    scene.clip_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/finalize", response_model=SceneRead)
def finalize_scene(scene_id: str, db: Session = Depends(get_db)):
    scene = _get_scene_or_404(db, scene_id)
    scene.clip_status = "final"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/keyframe", response_model=SceneRead)
def generate_keyframe(
    scene_id: str,
    db: Session = Depends(get_db),
    generator: ImageGenerator = Depends(get_image_generator),
    storage: Storage = Depends(get_storage),
):
    scene = _get_scene_or_404(db, scene_id)
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
def approve_keyframe(scene_id: str, db: Session = Depends(get_db)):
    scene = _get_scene_or_404(db, scene_id)
    scene.keyframe_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/clip/generate", response_model=JobRead)
def generate_clip(
    scene_id: str,
    db: Session = Depends(get_db),
    backend: VideoBackend = Depends(get_video_backend),
    storage: Storage = Depends(get_storage),
):
    scene = _get_scene_or_404(db, scene_id)
    if scene.keyframe_status != "approved" or not scene.keyframe_path:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Scene needs an approved keyframe before generating a clip",
        )

    def task(progress):
        progress(0.1)
        output = storage.project_dir(scene.project_id, "scenes", scene_id) / "clip.mp4"
        backend.generate(
            scene.keyframe_path,
            scene.video_prompt,
            scene.negative_prompt,
            str(output),
        )
        scene.clip_path = str(output)
        scene.clip_status = "generated"
        db.commit()
        return str(output)

    return execute_job(db, "clip", scene.project_id, task, scene_id=scene_id)


@router.post("/{scene_id}/clip/approve", response_model=SceneRead)
def approve_clip(scene_id: str, db: Session = Depends(get_db)):
    scene = _get_scene_or_404(db, scene_id)
    scene.clip_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene


@router.post("/{scene_id}/keyframe/upload", response_model=SceneRead)
def upload_keyframe(
    scene_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    scene = _get_scene_or_404(db, scene_id)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {file.content_type}",
        )
    path = storage.save_upload(
        scene.project_id,
        f"scenes/{scene_id}",
        f"keyframe{_image_suffix(file.filename)}",
        file.file,
    )
    scene.keyframe_path = str(path)
    scene.keyframe_status = "approved"
    db.commit()
    db.refresh(scene)
    return scene
