"""P5-S1 — Export presets (resolution / format / platform)."""
from ..schemas import ExportPresetRead

EXPORT_PRESETS: list[ExportPresetRead] = [
    ExportPresetRead(
        id="youtube_1080p", name="YouTube 1080p", platform="youtube",
        width=1920, height=1080, fps=24, format="mp4",
    ),
    ExportPresetRead(
        id="youtube_4k", name="YouTube 4K", platform="youtube",
        width=3840, height=2160, fps=24, format="mp4",
    ),
    ExportPresetRead(
        id="tiktok_vertical", name="TikTok / Reels (vertical)", platform="tiktok",
        width=1080, height=1920, fps=30, format="mp4",
    ),
    ExportPresetRead(
        id="instagram_square", name="Instagram (square)", platform="instagram",
        width=1080, height=1080, fps=30, format="mp4",
    ),
]

_BY_ID = {p.id: p for p in EXPORT_PRESETS}


def list_presets() -> list[ExportPresetRead]:
    return EXPORT_PRESETS


def get_preset(preset_id: str) -> ExportPresetRead | None:
    return _BY_ID.get(preset_id)
