"""P5-S6 — Local song generation adapter (ACE-Step).

The pipeline depends only on the ``SongGenerator`` protocol so tests inject a
fake and the local music model stays a swappable runtime detail. This removes
the manual audio-upload step from the workflow.
"""
import os
from typing import Protocol


class SongGenerator(Protocol):
    def generate(self, prompt: str, output_path: str, duration: int) -> str:
        ...


class AceStepGenerator:
    """Local song generation via ACE-Step. Not exercised by unit tests."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("ACESTEP_MODEL", "ace-step-v1")

    def generate(self, prompt: str, output_path: str, duration: int) -> str:
        from pathlib import Path

        from acestep.pipeline import ACEStepPipeline  # heavy, runtime-only

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pipeline = ACEStepPipeline(self.model)
        pipeline.generate(prompt=prompt, audio_duration=duration, output_path=output_path)
        return output_path
