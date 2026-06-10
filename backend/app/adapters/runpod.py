"""CB-2 — RunPod Serverless backends for image/video (our ComfyUI, elastic).

Builds our pinned ComfyUI workflow graph (substituting prompt/seed/resolution),
submits it to a RunPod Serverless endpoint, polls until completion, and writes the
returned asset. The RunPod handler is expected to run ComfyUI and return either a
base64 asset or a URL. Runtime detail — exercised via mocks, not real network.
"""
import base64
import random
import time
from pathlib import Path

import httpx

from ..comfyui.client import ComfyUIClient
from ..config import get_settings

DEFAULT_NEGATIVE = "flicker, jitter, deformed, watermark, text, low quality"
_TERMINAL_FAILURES = {"FAILED", "CANCELLED", "TIMED_OUT"}


class RunPodError(RuntimeError):
    """Raised when a RunPod job fails or the endpoint errors."""


class RunPodClient:
    """Submit a job to a RunPod Serverless endpoint and await its output."""

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        poll_interval: float = 1.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key or get_settings().runpod_api_key
        self.poll_interval = poll_interval

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def run(self, payload: dict) -> dict:
        timeout = get_settings().llm_timeout_seconds
        try:
            resp = httpx.post(
                f"{self.endpoint}/run",
                headers=self._headers,
                json={"input": payload},
                timeout=timeout,
            )
            resp.raise_for_status()
            job_id = resp.json()["id"]
            while True:
                status_resp = httpx.get(
                    f"{self.endpoint}/status/{job_id}",
                    headers=self._headers,
                    timeout=timeout,
                )
                status_resp.raise_for_status()
                data = status_resp.json()
                status = data.get("status")
                if status == "COMPLETED":
                    return data.get("output", {})
                if status in _TERMINAL_FAILURES:
                    raise RunPodError(
                        f"RunPod job {status}: {data.get('error', 'unknown')}"
                    )
                time.sleep(self.poll_interval)
        except httpx.HTTPError as exc:
            raise RunPodError(f"RunPod request failed: {exc}") from exc


def _write_output(output: dict, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    blob = output.get("image_base64") or output.get("base64")
    if blob:
        Path(output_path).write_bytes(base64.b64decode(blob))
        return
    if output.get("url"):
        resp = httpx.get(output["url"], timeout=get_settings().llm_timeout_seconds)
        resp.raise_for_status()
        Path(output_path).write_bytes(resp.content)
        return
    raise RunPodError("RunPod output contained no asset (image_base64/base64/url)")


class RunPodImageGenerator:
    """ImageGenerator backed by RunPod-hosted ComfyUI."""

    def __init__(self, client: RunPodClient | None = None, comfy: ComfyUIClient | None = None):
        self.client = client or RunPodClient(get_settings().runpod_image_endpoint)
        self.comfy = comfy or ComfyUIClient()

    def generate(self, workflow: str, params: dict, output_path: str) -> str:
        graph = self.comfy.build_workflow(workflow, params)
        _write_output(self.client.run({"workflow": graph}), output_path)
        return output_path

    def smoke_test(self) -> list[str]:
        return self.comfy.smoke_test()


class RunPodVideoBackend:
    """VideoBackend backed by RunPod-hosted ComfyUI."""

    def __init__(
        self,
        workflow: str,
        client: RunPodClient | None = None,
        comfy: ComfyUIClient | None = None,
    ):
        self.workflow = workflow
        self.client = client or RunPodClient(get_settings().runpod_video_endpoint)
        self.comfy = comfy or ComfyUIClient()

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
        params = {
            "KEYFRAME_IMAGE": keyframe_path,
            "POSITIVE_PROMPT": video_prompt,
            "NEGATIVE_PROMPT": negative_prompt or DEFAULT_NEGATIVE,
            "SEED": random.randint(0, 2**31 - 1) if seed is None else seed,
            "FRAMES": frames,
            "WIDTH": width,
            "HEIGHT": height,
        }
        graph = self.comfy.build_workflow(self.workflow, params)
        _write_output(self.client.run({"workflow": graph}), output_path)
        return output_path
