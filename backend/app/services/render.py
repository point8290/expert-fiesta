"""P1-S8 — Final render service.

Gathers approved clips in scene order, validates the project is renderable, and
delegates the actual stitch/mux to the ``Renderer`` adapter.
"""
from ..adapters.render import Renderer
from ..models import Audio, Project, Scene
from ..storage import Storage

APPROVED_STATUSES = {"approved", "final"}

# Output resolution per aspect ratio. Defaults to 16:9 1080p.
ASPECT_RESOLUTIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:3": (1440, 1080),
}
DEFAULT_FPS = 24


class RenderError(RuntimeError):
    """Raised when a project cannot be rendered (no audio, missing clips, etc.)."""


def render_project(
    project: Project,
    audio: Audio | None,
    scenes: list[Scene],
    renderer: Renderer,
    storage: Storage,
) -> str:
    if audio is None:
        raise RenderError("No audio uploaded for this project")
    if not scenes:
        raise RenderError("No scenes to render")

    ordered = sorted(scenes, key=lambda s: s.number)
    missing = [
        s.number
        for s in ordered
        if s.clip_status not in APPROVED_STATUSES or not s.clip_path
    ]
    if missing:
        raise RenderError(f"Scenes without an approved clip: {missing}")

    width, height = ASPECT_RESOLUTIONS.get(project.aspect_ratio, (1920, 1080))
    output_path = storage.project_dir(project.id, "renders") / "final.mp4"
    renderer.render(
        [s.clip_path for s in ordered],
        audio.path,
        str(output_path),
        width=width,
        height=height,
        fps=DEFAULT_FPS,
    )
    return str(output_path)
