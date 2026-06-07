"""P3-S1 / P4-S1 / P4-S2 — Video generation backends.

Every backend implements the same ``VideoBackend`` contract:
``(keyframe, videoPrompt, negativePrompt) -> clip.mp4``. The three local backends
(LTX-Video, Wan 2.2, HunyuanVideo) share the same parameter shape and only differ
by their committed ComfyUI workflow template, so they subclass ``ComfyVideoBackend``.
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


class ComfyVideoBackend:
    """Shared image-to-video backend driven by a named ComfyUI workflow."""

    workflow: str = ""

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


class LTXBackend(ComfyVideoBackend):
    """LTX-Video image-to-video (fast, the MVP default)."""

    workflow = "ltx_video"


class WanBackend(ComfyVideoBackend):
    """Wan 2.2 image-to-video."""

    workflow = "wan_video"


class HunyuanBackend(ComfyVideoBackend):
    """HunyuanVideo image-to-video."""

    workflow = "hunyuan_video"
