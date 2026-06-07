"""Final-render adapter. Stitches approved clips + audio into one MP4.

The pipeline depends only on the ``Renderer`` protocol so tests inject a fake and
the FFmpeg invocation stays an isolated detail. MVP uses hard cuts; crossfades
arrive in Phase 4.
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol


class Renderer(Protocol):
    def render(
        self,
        clips: list[str],
        audio_path: str,
        output_path: str,
        *,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        ...


class FFmpegRenderer:
    """Real renderer using FFmpeg. Not exercised by unit tests."""

    def render(
        self,
        clips: list[str],
        audio_path: str,
        output_path: str,
        *,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 1. Normalize every clip to the same resolution/fps/SAR so concat is safe.
        with tempfile.TemporaryDirectory() as tmp:
            normalized: list[str] = []
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"fps={fps},setsar=1"
            )
            for i, clip in enumerate(clips):
                out = str(Path(tmp) / f"norm_{i:03d}.mp4")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", clip, "-vf", vf, "-an", out],
                    check=True,
                )
                normalized.append(out)

            # 2. Concatenate normalized clips (hard cuts) via the concat demuxer.
            list_file = Path(tmp) / "concat.txt"
            list_file.write_text(
                "".join(f"file '{p}'\n" for p in normalized)
            )
            silent = str(Path(tmp) / "video.mp4")
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(list_file), "-c", "copy", silent,
                ],
                check=True,
            )

            # 3. Mux the song audio and trim to the shorter stream (the audio).
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", silent, "-i", audio_path,
                    "-c:v", "copy", "-c:a", "aac", "-shortest", output_path,
                ],
                check=True,
            )
        return output_path
