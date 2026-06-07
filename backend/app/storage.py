"""Filesystem storage for project assets (audio, images, clips, renders).

Layout (see docs/BUILD_PLAN.md §2):

    <base>/<projectId>/audio/<file>
    <base>/<projectId>/scenes/<sceneId>/keyframe.png
    <base>/<projectId>/renders/final.mp4
"""
import shutil
from pathlib import Path
from typing import BinaryIO


class Storage:
    def __init__(self, base_dir):
        self.base = Path(base_dir)

    def project_dir(self, project_id: str, *parts: str) -> Path:
        path = self.base / project_id / Path(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(
        self, project_id: str, subdir: str, filename: str, fileobj: BinaryIO
    ) -> Path:
        """Persist an uploaded file and return its absolute path."""
        dest = self.project_dir(project_id, subdir) / Path(filename).name
        with open(dest, "wb") as out:
            shutil.copyfileobj(fileobj, out)
        return dest
