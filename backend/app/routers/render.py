"""P1-S8 — Final render endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters.render import Renderer
from ..database import get_db
from ..dependencies import get_renderer, get_storage
from ..models import Audio, Project, Scene
from ..schemas import RenderRead
from ..services.render import RenderError, render_project
from ..storage import Storage

router = APIRouter(tags=["render"])


@router.post("/projects/{project_id}/render", response_model=RenderRead)
def render_final(
    project_id: str,
    db: Session = Depends(get_db),
    renderer: Renderer = Depends(get_renderer),
    storage: Storage = Depends(get_storage),
):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    audio = db.get(Audio, project_id)
    scenes = list(
        db.scalars(select(Scene).where(Scene.project_id == project_id))
    )

    try:
        output_path = render_project(project, audio, scenes, renderer, storage)
    except RenderError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    project.status = "rendered"
    db.commit()
    return RenderRead(
        project_id=project_id, status="completed", output_path=output_path
    )
