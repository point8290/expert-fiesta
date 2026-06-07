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


class CharacterContent(CamelModel):
    """The character fields produced by the LLM."""

    name: str
    age: str = ""
    face: str = ""
    hair: str = ""
    clothing: str = ""
    personality: str = ""
    identity_anchors: list[str] = []


class CharacterUpdate(CamelModel):
    name: Optional[str] = None
    age: Optional[str] = None
    face: Optional[str] = None
    hair: Optional[str] = None
    clothing: Optional[str] = None
    personality: Optional[str] = None
    identity_anchors: Optional[list[str]] = None


class CharacterRead(CamelModel):
    id: str
    project_id: str
    name: str
    age: str
    face: str
    hair: str
    clothing: str
    personality: str
    identity_anchors: list[str]
    ref_image_path: Optional[str] = None
    ref_status: str


class SceneContent(CamelModel):
    """The descriptive fields the LLM produces for one scene (no timing)."""

    visual_description: str
    camera_instruction: str
    motion_instruction: str
    keyframe_prompt: str
    video_prompt: str
    negative_prompt: str


class PromptVersionRead(CamelModel):
    id: str
    scene_id: str
    version: int
    keyframe_prompt: str
    video_prompt: str
    negative_prompt: str
    created_at: datetime


class SceneUpdate(CamelModel):
    visual_description: Optional[str] = None
    camera_instruction: Optional[str] = None
    motion_instruction: Optional[str] = None
    keyframe_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None


class SceneRead(CamelModel):
    id: str
    project_id: str
    number: int
    start_time: float
    end_time: float
    duration_seconds: float
    section_name: str
    visual_description: str
    camera_instruction: str
    motion_instruction: str
    keyframe_prompt: str
    video_prompt: str
    negative_prompt: str
    keyframe_path: Optional[str] = None
    keyframe_status: str
    keyframe_prompt_version: Optional[int] = None
    clip_path: Optional[str] = None
    clip_status: str
    clip_prompt_version: Optional[int] = None


class JobRead(CamelModel):
    id: str
    project_id: str
    scene_id: Optional[str] = None
    type: str
    status: str
    progress: float
    error: Optional[str] = None
    result_path: Optional[str] = None
    created_at: datetime
    queue_position: Optional[int] = None


class RenderRead(CamelModel):
    project_id: str
    status: str
    output_path: str


class LyricsData(CamelModel):
    """The structured lyrics payload produced by the LLM and returned by the API."""

    title: str = Field(min_length=1)
    structure: list[str]
    body: str = Field(min_length=1)
    music_prompt: str = Field(min_length=1)
    emotional_arc: str = Field(min_length=1)
