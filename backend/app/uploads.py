"""PR0-7 — shared upload-size enforcement."""
from fastapi import HTTPException, UploadFile

from .config import get_settings


def enforce_upload_size(file: UploadFile) -> None:
    cap_mb = get_settings().max_upload_mb
    if (file.size or 0) > cap_mb * 1024 * 1024:
        raise HTTPException(
            413, detail=f"File exceeds the {cap_mb} MB upload limit"
        )
