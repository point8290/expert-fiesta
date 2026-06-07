"""P5-S2 — Ownership guards.

Every project-scoped resource is reachable only by the project's owner. Unknown
*and* unauthorized lookups both return 404 so existence isn't leaked.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import Character, Project, Scene, User


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


def require_project(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise _not_found("Project")
    return project


def require_scene(db: Session, scene_id: str, user: User) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise _not_found("Scene")
    owner = db.get(Project, scene.project_id)
    if owner is None or owner.owner_id != user.id:
        raise _not_found("Scene")
    return scene


def require_character(db: Session, character_id: str, user: User) -> Character:
    character = db.get(Character, character_id)
    if character is None:
        raise _not_found("Character")
    owner = db.get(Project, character.project_id)
    if owner is None or owner.owner_id != user.id:
        raise _not_found("Character")
    return character
