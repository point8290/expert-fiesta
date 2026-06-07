"""Scene clip generation — shared by the request path and the background worker."""
from ..models import Project, Scene
from ..services.prompt_versions import latest_version_number
from ..storage import Storage
from ..video.backends import VideoBackend


class BackendError(RuntimeError):
    """Raised when the requested video backend isn't available."""


def resolve_backend(
    registry: dict[str, VideoBackend], project: Project, scene: Scene
) -> VideoBackend:
    # P5-S4: a per-scene override takes precedence over the project's backend.
    name = scene.video_backend_override or project.video_backend
    backend = registry.get(name)
    if backend is None:
        raise BackendError(f"Unknown video backend: {name}")
    return backend


def generate_clip_for_scene(
    db, scene: Scene, backend: VideoBackend, storage: Storage
) -> str:
    """Render the scene's clip from its approved keyframe and persist the result."""
    output = storage.project_dir(scene.project_id, "scenes", scene.id) / "clip.mp4"
    backend.generate(
        scene.keyframe_path,
        scene.video_prompt,
        scene.negative_prompt,
        str(output),
    )
    scene.clip_path = str(output)
    scene.clip_status = "generated"
    scene.clip_prompt_version = latest_version_number(db, scene.id)
    db.commit()
    return str(output)
