"""P5-S3 — Project export / import.

Export produces a portable JSON snapshot of a project's metadata (project,
lyrics, characters, scenes). Import recreates it as a brand-new project with
fresh ids. Generated *assets* (images/clips) are not bundled, so imported
keyframes/clips start in the ``pending`` state.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Character, Lyrics, Project, Scene
from ..schemas import (
    CharacterRead,
    LyricsData,
    ProjectExport,
    ProjectRead,
    SceneRead,
)


def export_project(db: Session, project: Project) -> ProjectExport:
    lyrics = db.get(Lyrics, project.id)
    characters = db.scalars(
        select(Character).where(Character.project_id == project.id)
    )
    scenes = db.scalars(
        select(Scene).where(Scene.project_id == project.id).order_by(Scene.number)
    )
    return ProjectExport(
        project=ProjectRead.model_validate(project),
        lyrics=LyricsData.model_validate(lyrics) if lyrics else None,
        characters=[CharacterRead.model_validate(c) for c in characters],
        scenes=[SceneRead.model_validate(s) for s in scenes],
    )


def import_project(
    db: Session, export: ProjectExport, owner_id: str | None = None
) -> Project:
    src = export.project
    project = Project(
        owner_id=owner_id,
        title=src.title,
        idea=src.idea,
        genre=src.genre,
        mood=src.mood,
        visual_style=src.visual_style,
        target_duration=src.target_duration,
        aspect_ratio=src.aspect_ratio,
        video_backend=src.video_backend,
        transition=src.transition,
        transition_duration=src.transition_duration,
    )
    db.add(project)
    db.flush()  # assign project.id

    if export.lyrics:
        db.add(
            Lyrics(
                project_id=project.id,
                title=export.lyrics.title,
                structure=export.lyrics.structure,
                body=export.lyrics.body,
                music_prompt=export.lyrics.music_prompt,
                emotional_arc=export.lyrics.emotional_arc,
            )
        )

    for c in export.characters:
        db.add(
            Character(
                project_id=project.id,
                name=c.name,
                age=c.age,
                face=c.face,
                hair=c.hair,
                clothing=c.clothing,
                personality=c.personality,
                identity_anchors=c.identity_anchors,
                lora_path=c.lora_path,
            )
        )

    for s in export.scenes:
        # Copy the storyboard but not the generated assets.
        db.add(
            Scene(
                project_id=project.id,
                number=s.number,
                start_time=s.start_time,
                end_time=s.end_time,
                duration_seconds=s.duration_seconds,
                section_name=s.section_name,
                visual_description=s.visual_description,
                camera_instruction=s.camera_instruction,
                motion_instruction=s.motion_instruction,
                keyframe_prompt=s.keyframe_prompt,
                video_prompt=s.video_prompt,
                negative_prompt=s.negative_prompt,
            )
        )

    db.commit()
    db.refresh(project)
    return project
