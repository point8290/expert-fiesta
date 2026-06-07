"""P1-S8 — Final render endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import os

from fastapi.responses import FileResponse

from ..adapters.render import Renderer
from ..database import get_db
from ..dependencies import get_current_user, get_renderer, get_storage
from ..models import Audio, Scene, User
from ..ownership import require_project
from ..schemas import RenderRead
from ..services.export_presets import get_preset
from ..services.render import RenderError, render_project
from ..storage import Storage

router = APIRouter(tags=["render"])


@router.get("/projects/{project_id}/render/file")
def serve_render(
    project_id: str,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
    path = storage.project_dir(project_id, "renders") / "final.mp4"
    if not os.path.exists(path):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="No render yet for this project"
        )
    return FileResponse(str(path), filename="final.mp4")


@router.post("/projects/{project_id}/render", response_model=RenderRead)
def render_final(
    project_id: str,
    preset: str | None = None,
    db: Session = Depends(get_db),
    renderer: Renderer = Depends(get_renderer),
    storage: Storage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)

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
