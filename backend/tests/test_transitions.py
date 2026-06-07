"""Tests for P4-S5 — Transitions (crossfade in addition to hard cuts)."""
from pathlib import Path

from app.models import Audio, Project, Scene
from app.services.render import render_project
from app.storage import Storage


class FakeRenderer:
    def __init__(self):
        self.kwargs = None

    def render(
        self,
        clips,
        audio_path,
        output_path,
        *,
        width,
        height,
        fps,
        transition,
        transition_duration,
    ):
        self.kwargs = {
            "transition": transition,
            "transition_duration": transition_duration,
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"FINAL")
        return output_path


def _project(transition="cut", duration=0.5):
    p = Project(
        title="t",
        idea="i",
        genre="g",
        mood="m",
        visual_style="v",
        target_duration=40,
        aspect_ratio="16:9",
    )
    p.id = "p1"
    p.transition = transition
    p.transition_duration = duration
    return p


def _scene(n, path):
    s = Scene(
        project_id="p1",
        number=n,
        start_time=0,
        end_time=5,
        duration_seconds=5,
    )
    s.clip_status = "approved"
    s.clip_path = path
    return s


def _audio():
    a = Audio()
    a.path = "/tmp/song.wav"
    return a


def test_render_passes_crossfade_transition(tmp_path):
    renderer = FakeRenderer()
    project = _project(transition="crossfade", duration=0.7)
    scenes = [_scene(1, "/tmp/a.mp4"), _scene(2, "/tmp/b.mp4")]
    render_project(project, _audio(), scenes, renderer, Storage(tmp_path))
    assert renderer.kwargs["transition"] == "crossfade"
    assert renderer.kwargs["transition_duration"] == 0.7


def test_render_defaults_to_hard_cut(tmp_path):
    renderer = FakeRenderer()
    project = _project(transition="cut")
    scenes = [_scene(1, "/tmp/a.mp4")]
    render_project(project, _audio(), scenes, renderer, Storage(tmp_path))
    assert renderer.kwargs["transition"] == "cut"


def test_new_project_defaults_transition_to_cut(client, project_payload):
    project = client.post("/projects", json=project_payload).json()
    assert project["transition"] == "cut"
    # And it is selectable via PATCH.
    patched = client.patch(
        f"/projects/{project['id']}", json={"transition": "crossfade"}
    )
    assert patched.json()["transition"] == "crossfade"
