"""Tests for P5-S1 — Project templates + export presets."""
from pathlib import Path

from app.models import Audio, Project, Scene
from app.services.export_presets import get_preset
from app.services.render import render_project
from app.storage import Storage


# --- templates --------------------------------------------------------------

def test_list_templates(client):
    res = client.get("/templates")
    assert res.status_code == 200
    templates = res.json()
    ids = {t["id"] for t in templates}
    assert "cinematic_pop_rock" in ids
    assert any(t["aspectRatio"] == "9:16" for t in templates)
    # Templates carry default project fields.
    t = next(t for t in templates if t["id"] == "cinematic_pop_rock")
    assert t["genre"] and t["visualStyle"] and t["videoBackend"]


def test_create_project_from_template(client):
    res = client.post(
        "/projects/from-template/cinematic_pop_rock",
        json={"title": "Wings", "idea": "two friends and birds"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Wings"
    assert body["idea"] == "two friends and birds"
    # Template-provided fields are applied.
    assert body["aspectRatio"] == "16:9"
    assert body["genre"]


def test_create_from_unknown_template_returns_404(client):
    res = client.post(
        "/projects/from-template/nope", json={"title": "x", "idea": "y"}
    )
    assert res.status_code == 404


# --- export presets ---------------------------------------------------------

def test_list_export_presets(client):
    res = client.get("/export-presets")
    assert res.status_code == 200
    presets = {p["id"]: p for p in res.json()}
    assert "youtube_1080p" in presets
    assert presets["youtube_1080p"]["width"] == 1920
    assert presets["youtube_1080p"]["height"] == 1080
    assert "tiktok_vertical" in presets
    assert presets["tiktok_vertical"]["height"] == 1920


# --- preset applied at render -----------------------------------------------

class FakeRenderer:
    def __init__(self):
        self.kwargs = None

    def render(self, clips, audio_path, output_path, *, width, height, **rest):
        self.kwargs = {"width": width, "height": height, **rest}
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"x")
        return output_path


def _project():
    p = Project(
        title="t", idea="i", genre="g", mood="m", visual_style="v",
        target_duration=40, aspect_ratio="16:9",
    )
    p.id = "p1"
    p.transition = "cut"
    p.transition_duration = 0.5
    return p


def _scene(path):
    s = Scene(project_id="p1", number=1, start_time=0, end_time=5, duration_seconds=5)
    s.clip_status = "approved"
    s.clip_path = path
    return s


def _audio():
    a = Audio()
    a.path = "/tmp/song.wav"
    return a


def test_render_with_preset_overrides_resolution(tmp_path):
    renderer = FakeRenderer()
    preset = get_preset("tiktok_vertical")
    render_project(
        _project(), _audio(), [_scene("/tmp/a.mp4")], renderer, Storage(tmp_path),
        preset=preset,
    )
    assert renderer.kwargs["width"] == 1080
    assert renderer.kwargs["height"] == 1920


def test_render_without_preset_uses_aspect_ratio(tmp_path):
    renderer = FakeRenderer()
    render_project(
        _project(), _audio(), [_scene("/tmp/a.mp4")], renderer, Storage(tmp_path)
    )
    assert renderer.kwargs["width"] == 1920
    assert renderer.kwargs["height"] == 1080
