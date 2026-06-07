"""P1-S3 — Upload project audio."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..adapters.audio_analysis import AudioAnalyzer
from ..adapters.song import SongGenerator
from ..database import get_db
from ..dependencies import (
    get_audio_analyzer,
    get_current_user,
    get_song_generator,
    get_storage,
)
from ..models import Audio, Lyrics, User
from ..ownership import require_project
from ..schemas import AudioRead
from ..storage import Storage

router = APIRouter(prefix="/projects/{project_id}/audio", tags=["audio"])

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/vnd.wave",
}


@router.post("", response_model=AudioRead, status_code=status.HTTP_201_CREATED)
def upload_audio(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type: {file.content_type}",
        )

    path = storage.save_upload(project_id, "audio", file.filename, file.file)
    row = db.merge(
        Audio(
            project_id=project_id,
            filename=file.filename,
            content_type=file.content_type,
            path=str(path),
            source="upload",
        )
    )
    db.commit()
    return AudioRead.model_validate(row)


@router.get("", response_model=AudioRead)
def get_audio(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
    row = db.get(Audio, project_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    return AudioRead.model_validate(row)


@router.post("/generate", response_model=AudioRead, status_code=status.HTTP_201_CREATED)
def generate_song(
    project_id: str,
    db: Session = Depends(get_db),
    generator: SongGenerator = Depends(get_song_generator),
    storage: Storage = Depends(get_storage),
    current_user: User = Depends(get_current_user),
):
    project = require_project(db, project_id, current_user)
    lyrics = db.get(Lyrics, project_id)
    if lyrics is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Generate lyrics first — the music prompt drives song generation",
        )
    path = storage.project_dir(project_id, "audio") / "song.wav"
    generator.generate(lyrics.music_prompt, str(path), project.target_duration)
    row = db.merge(
        Audio(
            project_id=project_id,
            filename="song.wav",
            content_type="audio/wav",
            path=str(path),
            source="generated",
        )
    )
    db.commit()
    return AudioRead.model_validate(row)


@router.post("/analyze", response_model=AudioRead)
def analyze_audio(
    project_id: str,
    db: Session = Depends(get_db),
    analyzer: AudioAnalyzer = Depends(get_audio_analyzer),
    current_user: User = Depends(get_current_user),
):
    require_project(db, project_id, current_user)
    row = db.get(Audio, project_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")

    analysis = analyzer.analyze(row.path)
    row.duration_seconds = analysis.duration_seconds
    row.bpm = analysis.bpm
    row.beats = analysis.beats
    row.sections = analysis.sections
    row.waveform = analysis.waveform
    db.commit()
    db.refresh(row)
    return AudioRead.model_validate(row)
