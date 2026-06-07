"""P3-S1 — Video generation backends.

Every backend implements the same ``VideoBackend`` contract:
``(keyframe, videoPrompt, negativePrompt) -> clip.mp4``. This is the swap point
for LTX-Video (here) and, in Phase 4, Wan 2.2 and HunyuanVideo.
"""
import random
from typing import Protocol

from ..comfyui.client import ComfyUIClient

DEFAULT_NEGATIVE = "flicker, jitter, deformed, watermark, text, low quality"


class VideoBackend(Protocol):
    workflow: str

    def generate(
        self,
        keyframe_path: str,
        video_prompt: str,
        negative_prompt: str,
        output_path: str,
        *,
        seed: int | None = None,
        frames: int = 120,
    ) -> str:
        ...


class LTXBackend:
    """LTX-Video image-to-video via a committed ComfyUI workflow."""

    workflow = "ltx_video"

    def __init__(self, comfy: ComfyUIClient | None = None):
        self.comfy = comfy or ComfyUIClient()

    def params(
        self,
        keyframe_path: str,
        video_prompt: str,
        negative_prompt: str,
        seed: int,
        frames: int,
        width: int,
        height: int,
    ) -> dict:
        return {
            "KEYFRAME_IMAGE": keyframe_path,
            "POSITIVE_PROMPT": video_prompt,
            "NEGATIVE_PROMPT": negative_prompt or DEFAULT_NEGATIVE,
            "SEED": seed,
            "FRAMES": frames,
            "WIDTH": width,
            "HEIGHT": height,
        }

    def generate(
        self,
        keyframe_path: str,
        video_prompt: str,
        negative_prompt: str,
        output_path: str,
        *,
        seed: int | None = None,
        frames: int = 120,
        width: int = 768,
        height: int = 512,
    ) -> str:
        seed = random.randint(0, 2**31 - 1) if seed is None else seed
        params = self.params(
            keyframe_path, video_prompt, negative_prompt, seed, frames, width, height
        )
        # Runtime: submit to ComfyUI and download the produced clip.
        self.comfy.generate(self.workflow, params, output_path)
        return output_path
