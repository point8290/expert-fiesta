"""P1-S1 — Create and manage projects (owner-scoped, P5-S2)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Project, User
from ..ownership import require_project
from ..schemas import (
    ProjectCreate,
    ProjectExport,
    ProjectFromTemplate,
    ProjectRead,
    ProjectUpdate,
)
from ..services.export_import import export_project, import_project
from ..services.templates import get_template

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(**payload.model_dump(), owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post(
    "/from-template/{template_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_from_template(
    template_id: str,
    payload: ProjectFromTemplate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template not found")
    project = Project(
        owner_id=current_user.id,
        title=payload.title,
        idea=payload.idea,
        genre=template.genre,
        mood=template.mood,
        visual_style=template.visual_style,
        target_duration=template.target_duration,
        aspect_ratio=template.aspect_ratio,
        video_backend=template.video_backend,
        transition=template.transition,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post(
    "/import", response_model=ProjectRead, status_code=status.HTTP_201_CREATED
)
def import_project_endpoint(
    payload: ProjectExport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return import_project(db, payload, owner_id=current_user.id)


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/{project_id}/export", response_model=ProjectExport)
def export_project_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)
    return export_project(db, project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_project(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)
    db.delete(project)
    db.commit()
