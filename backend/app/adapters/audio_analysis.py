"""Audio analysis adapter. Extracts timing features used by the storyboard.

The pipeline depends only on the ``AudioAnalyzer`` protocol so tests inject a
fake and the real implementation (librosa) stays an isolated, swappable detail.
"""
from typing import Protocol

from ..schemas import AudioAnalysis


class AudioAnalyzer(Protocol):
    def analyze(self, path: str) -> AudioAnalysis:
        ...


class LibrosaAnalyzer:
    """Real analyzer backed by librosa. Not exercised by unit tests."""

    WAVEFORM_POINTS = 200

    def analyze(self, path: str) -> AudioAnalysis:
        import librosa
        import numpy as np

        y, sr = librosa.load(path, mono=True)
        duration = float(librosa.get_duration(y=y, sr=sr))
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Downsample an amplitude envelope for the waveform display.
        hop = max(1, len(y) // self.WAVEFORM_POINTS)
        waveform = [
            float(np.abs(y[i : i + hop]).max())
            for i in range(0, len(y), hop)
        ][: self.WAVEFORM_POINTS]

        return AudioAnalysis(
            duration_seconds=duration,
            bpm=float(tempo),
            beats=beats,
            sections=self._rough_sections(duration),
            waveform=waveform,
        )

    @staticmethod
    def _rough_sections(duration: float) -> list:
        """Naive equal-split sections; refined segmentation comes in Phase 4."""
        names = ["intro", "verse", "chorus", "outro"]
        step = duration / len(names)
        return [
            {"name": name, "start": round(i * step, 2), "end": round((i + 1) * step, 2)}
            for i, name in enumerate(names)
        ]
