"""P1-S1 — Create and manage projects."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project
from ..schemas import (
    ProjectCreate,
    ProjectFromTemplate,
    ProjectRead,
    ProjectUpdate,
)
from ..services.templates import get_template

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
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
):
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Template not found")
    project = Project(
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


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    stmt = select(Project).order_by(Project.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)
):
    project = _get_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = _get_or_404(db, project_id)
    db.delete(project)
    db.commit()
