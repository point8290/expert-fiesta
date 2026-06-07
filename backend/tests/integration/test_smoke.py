"""PR1-8 — real-dependency smoke tests.

Excluded from the default unit run (see pytest.ini). Run explicitly:

    pytest -m integration

They exercise the actual adapters the unit suite mocks, skipping cleanly when a
dependency (ffmpeg, librosa, a running Ollama/ComfyUI) isn't present.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


@pytest.mark.skipif(not _has("ffmpeg"), reason="ffmpeg not installed")
def test_ffmpeg_render_produces_mp4(tmp_path):
    """A real FFmpeg pass concatenates clips + audio into a playable MP4."""
    from app.adapters.render import FFmpegRenderer

    # Synthesize two short test clips + a silent audio track with ffmpeg.
    clips = []
    for i in range(2):
        clip = tmp_path / f"clip{i}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration=1:size=320x240:rate=24",
             "-pix_fmt", "yuv420p", str(clip)],
            check=True, capture_output=True,
        )
        clips.append(str(clip))
    audio = tmp_path / "a.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", "2", str(audio)],
        check=True, capture_output=True,
    )

    out = tmp_path / "final.mp4"
    FFmpegRenderer().render(
        clips, str(audio), str(out), width=320, height=240, fps=24
    )
    assert Path(out).exists() and Path(out).stat().st_size > 0


@pytest.mark.skipif("librosa" not in globals() and not _has("python"), reason="librosa optional")
def test_librosa_analysis_runs(tmp_path):
    """LibrosaAnalyzer returns features for a real wav (needs requirements-ml)."""
    librosa = pytest.importorskip("librosa")  # noqa: F841
    if not _has("ffmpeg"):
        pytest.skip("ffmpeg needed to synthesize the test wav")
    wav = tmp_path / "tone.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(wav)],
        check=True, capture_output=True,
    )
    from app.adapters.audio_analysis import LibrosaAnalyzer

    result = LibrosaAnalyzer().analyze(str(wav))
    assert result.duration_seconds > 0
    assert result.bpm >= 0
