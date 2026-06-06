"""P2-S1 — ComfyUI media adapter.

Runs parameterized ComfyUI workflows. Templates are committed JSON graphs with
``{{PLACEHOLDER}}`` tokens; the client substitutes prompt/seed/resolution while
preserving value types, submits the graph to ComfyUI, waits for completion over
the WebSocket, and downloads the resulting image.

Only the pure pieces (template load, injection, smoke-test) are unit-tested; the
HTTP/WebSocket transport in ``generate`` is an isolated runtime detail.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Protocol

TEMPLATES_DIR = Path(__file__).parent / "templates"
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class MediaWorkflowError(RuntimeError):
    """Raised for missing templates, missing params, or generation failures."""


class ImageGenerator(Protocol):
    def generate(self, workflow: str, params: dict, output_path: str) -> str:
        ...

    def smoke_test(self) -> list[str]:
        ...


def _substitute(node: Any, params: dict) -> Any:
    if isinstance(node, dict):
        return {k: _substitute(v, params) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute(v, params) for v in node]
    if isinstance(node, str):
        exact = _PLACEHOLDER.fullmatch(node)
        if exact:
            key = exact.group(1)
            if key not in params:
                raise MediaWorkflowError(f"Missing workflow parameter: {key}")
            return params[key]  # preserve the original value's type
        # Inline placeholders inside a larger string become text.
        def repl(m: re.Match) -> str:
            key = m.group(1)
            if key not in params:
                raise MediaWorkflowError(f"Missing workflow parameter: {key}")
            return str(params[key])

        return _PLACEHOLDER.sub(repl, node)
    return node


class ComfyUIClient:
    def __init__(self, host: str | None = None, templates_dir: Path | None = None):
        self.host = host or os.environ.get("COMFYUI_HOST", "http://localhost:8188")
        self.templates_dir = Path(templates_dir or TEMPLATES_DIR)

    def load_template(self, name: str) -> dict:
        path = self.templates_dir / f"{name}.json"
        if not path.exists():
            raise MediaWorkflowError(f"Unknown workflow template: {name}")
        return json.loads(path.read_text())

    def build_workflow(self, name: str, params: dict) -> dict:
        return _substitute(self.load_template(name), params)

    def smoke_test(self) -> list[str]:
        """Parse every committed template; return the names that loaded."""
        names: list[str] = []
        for path in sorted(self.templates_dir.glob("*.json")):
            json.loads(path.read_text())
            names.append(path.stem)
        return names

    def generate(self, workflow: str, params: dict, output_path: str) -> str:
        """Submit a workflow to ComfyUI and write the output image. Runtime only."""
        import httpx
        from websocket import create_connection  # websocket-client

        graph = self.build_workflow(workflow, params)
        client_id = os.urandom(8).hex()

        resp = httpx.post(
            f"{self.host}/prompt",
            json={"prompt": graph, "client_id": client_id},
            timeout=30,
        )
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]

        ws_host = self.host.replace("http://", "ws://").replace("https://", "wss://")
        ws = create_connection(f"{ws_host}/ws?clientId={client_id}", timeout=600)
        try:
            while True:
                message = ws.recv()
                if not isinstance(message, str):
                    continue
                event = json.loads(message)
                if (
                    event.get("type") == "executing"
                    and event.get("data", {}).get("node") is None
                    and event.get("data", {}).get("prompt_id") == prompt_id
                ):
                    break
        finally:
            ws.close()

        history = httpx.get(f"{self.host}/history/{prompt_id}", timeout=30).json()
        images = self._first_image(history.get(prompt_id, {}))
        if not images:
            raise MediaWorkflowError("ComfyUI returned no image for the workflow")

        img = httpx.get(f"{self.host}/view", params=images, timeout=60)
        img.raise_for_status()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(img.content)
        return output_path

    @staticmethod
    def _first_image(history_entry: dict) -> dict | None:
        for node_output in history_entry.get("outputs", {}).values():
            for image in node_output.get("images", []):
                return {
                    "filename": image["filename"],
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
        return None
