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
        transition: str = "cut",
        transition_duration: float = 0.5,
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
        transition: str = "cut",
        transition_duration: float = 0.5,
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

            # 2. Join the normalized clips: hard cuts (concat) or crossfades (xfade).
            silent = str(Path(tmp) / "video.mp4")
            if transition == "crossfade" and len(normalized) > 1:
                self._xfade(normalized, fps, transition_duration, silent)
            else:
                list_file = Path(tmp) / "concat.txt"
                list_file.write_text(
                    "".join(f"file '{p}'\n" for p in normalized)
                )
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

    @staticmethod
    def _probe_duration(path: str) -> float:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(out.stdout.strip())

    def _xfade(
        self, clips: list[str], fps: int, duration: float, output_path: str
    ) -> None:
        """Chain clips with crossfades using the ffmpeg xfade filter."""
        inputs: list[str] = []
        for clip in clips:
            inputs += ["-i", clip]

        # Build a chain: each xfade offset = cumulative duration minus overlaps.
        filters: list[str] = []
        prev = "[0:v]"
        offset = self._probe_duration(clips[0]) - duration
        for i in range(1, len(clips)):
            label = f"[v{i}]" if i < len(clips) - 1 else "[vout]"
            filters.append(
                f"{prev}[{i}:v]xfade=transition=fade:duration={duration}:"
                f"offset={offset:.3f}{label}"
            )
            prev = label
            offset += self._probe_duration(clips[i]) - duration

        subprocess.run(
            [
                "ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(filters),
                "-map", "[vout]", "-r", str(fps), output_path,
            ],
            check=True,
        )
