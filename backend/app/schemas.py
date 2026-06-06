"""Pydantic schemas (API contract). camelCase on the wire, snake_case in models."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base that serializes to camelCase and accepts camelCase or snake_case."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ProjectCreate(CamelModel):
    title: str = Field(min_length=1)
    idea: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    mood: str = Field(min_length=1)
    visual_style: str = Field(min_length=1)
    target_duration: int = Field(gt=0)
    aspect_ratio: str = Field(min_length=1)


class ProjectUpdate(CamelModel):
    title: Optional[str] = None
    idea: Optional[str] = None
    genre: Optional[str] = None
    mood: Optional[str] = None
    visual_style: Optional[str] = None
    target_duration: Optional[int] = Field(default=None, gt=0)
    aspect_ratio: Optional[str] = None


class ProjectRead(CamelModel):
    id: str
    title: str
    idea: str
    genre: str
    mood: str
    visual_style: str
    target_duration: int
    aspect_ratio: str
    status: str
    created_at: datetime
    updated_at: datetime


class AudioAnalysis(CamelModel):
    """Features extracted from an audio track, used to time the storyboard."""

    duration_seconds: float
    bpm: float
    beats: list[float]
    sections: list
    waveform: list[float]


class AudioRead(CamelModel):
    project_id: str
    filename: str
    content_type: str
    source: str
    duration_seconds: Optional[float] = None
    bpm: Optional[float] = None
    beats: Optional[list[float]] = None
    sections: Optional[list] = None
    waveform: Optional[list[float]] = None


class LyricsData(CamelModel):
    """The structured lyrics payload produced by the LLM and returned by the API."""

    title: str = Field(min_length=1)
    structure: list[str]
    body: str = Field(min_length=1)
    music_prompt: str = Field(min_length=1)
    emotional_arc: str = Field(min_length=1)
