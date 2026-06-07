"""P1-S8 — Final render endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters.render import Renderer
from ..database import get_db
from ..dependencies import get_renderer, get_storage
from ..models import Audio, Project, Scene
from ..schemas import RenderRead
from ..services.export_presets import get_preset
from ..services.render import RenderError, render_project
from ..storage import Storage

router = APIRouter(tags=["render"])


@router.post("/projects/{project_id}/render", response_model=RenderRead)
def render_final(
    project_id: str,
    preset: str | None = None,
    db: Session = Depends(get_db),
    renderer: Renderer = Depends(get_renderer),
    storage: Storage = Depends(get_storage),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    resolved_preset = None
    if preset is not None:
        resolved_preset = get_preset(preset)
        if resolved_preset is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=f"Unknown export preset: {preset}"
            )

    audio = db.get(Audio, project_id)
    scenes = list(
        db.scalars(select(Scene).where(Scene.project_id == project_id))
    )

    try:
        output_path = render_project(
            project, audio, scenes, renderer, storage, preset=resolved_preset
        )
    except RenderError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    project.status = "rendered"
    db.commit()
    return RenderRead(
        project_id=project_id, status="completed", output_path=output_path
    )
