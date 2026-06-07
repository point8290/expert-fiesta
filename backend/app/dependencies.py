"""Shared FastAPI dependencies. Tests override these via ``app.dependency_overrides``."""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import get_settings
from .adapters.audio_analysis import AudioAnalyzer, LibrosaAnalyzer
from .adapters.consistency import ConsistencyScorer, FaceEmbeddingScorer
from .adapters.llm import LLMClient, OllamaClient
from .adapters.render import FFmpegRenderer, Renderer
from .adapters.song import AceStepGenerator, SongGenerator
from .comfyui.client import ComfyUIClient, ImageGenerator
from .database import get_db
from .models import User
from .services.auth import decode_token
from .storage import Storage
from .video.backends import VideoBackend
from .video.registry import build_registry


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer token (P5-S2)."""
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise credentials_error
    user_id = decode_token(authorization.split(" ", 1)[1])
    if user_id is None:
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def get_llm_client() -> LLMClient:
    return OllamaClient()


def get_storage() -> Storage:
    return Storage(get_settings().storage_dir)


def get_audio_analyzer() -> AudioAnalyzer:
    return LibrosaAnalyzer()


def get_renderer() -> Renderer:
    return FFmpegRenderer()


def get_image_generator() -> ImageGenerator:
    return ComfyUIClient()


def get_video_registry() -> dict[str, VideoBackend]:
    """All available video backends, keyed by name; project selects one."""
    return build_registry()


def get_consistency_scorer() -> ConsistencyScorer:
    return FaceEmbeddingScorer()


def get_song_generator() -> SongGenerator:
    return AceStepGenerator()
