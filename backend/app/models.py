"""SQLAlchemy models. The scene graph is the source of truth for the pipeline.

Phase 1 introduces ``Project``. Later phases extend this module with Audio,
Lyrics, Character, Scene, and Job tables (see docs/BUILD_PLAN.md §2).
"""
import uuid
from datetime import datetime, timezone

from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    idea: Mapped[str] = mapped_column(String, nullable=False)
    genre: Mapped[str] = mapped_column(String, nullable=False)
    mood: Mapped[str] = mapped_column(String, nullable=False)
    visual_style: Mapped[str] = mapped_column(String, nullable=False)
    target_duration: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )


class Lyrics(Base):
    """One set of lyrics per project (regenerating replaces the existing row)."""

    __tablename__ = "lyrics"

    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    structure: Mapped[list] = mapped_column(JSON, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    music_prompt: Mapped[str] = mapped_column(String, nullable=False)
    emotional_arc: Mapped[str] = mapped_column(String, nullable=False)


class Scene(Base):
    """One storyboard scene. Keyframe/clip fields are populated in Phases 2-3."""

    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    section_name: Mapped[str] = mapped_column(String, default="")
    visual_description: Mapped[str] = mapped_column(String, default="")
    camera_instruction: Mapped[str] = mapped_column(String, default="")
    motion_instruction: Mapped[str] = mapped_column(String, default="")
    keyframe_prompt: Mapped[str] = mapped_column(String, default="")
    video_prompt: Mapped[str] = mapped_column(String, default="")
    negative_prompt: Mapped[str] = mapped_column(String, default="")
    keyframe_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    keyframe_status: Mapped[str] = mapped_column(String, default="pending")
    clip_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    clip_status: Mapped[str] = mapped_column(String, default="pending")


class Character(Base):
    """A character in the project's bible. Identity anchors drive consistency."""

    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[str] = mapped_column(String, default="")
    face: Mapped[str] = mapped_column(String, default="")
    hair: Mapped[str] = mapped_column(String, default="")
    clothing: Mapped[str] = mapped_column(String, default="")
    personality: Mapped[str] = mapped_column(String, default="")
    identity_anchors: Mapped[list] = mapped_column(JSON, default=list)
    ref_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ref_status: Mapped[str] = mapped_column(String, default="pending")


class Audio(Base):
    """One audio track per project. Analysis fields (P1-S4) are filled in later."""

    __tablename__ = "audio"

    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="upload")
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    beats: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    sections: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    waveform: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
