"""P5-S1 — Catalog endpoints: project templates + export presets."""
from fastapi import APIRouter

from ..schemas import ExportPresetRead, ProjectTemplateRead
from ..services.export_presets import list_presets
from ..services.templates import list_templates

router = APIRouter(tags=["catalog"])


@router.get("/templates", response_model=list[ProjectTemplateRead])
def get_templates():
    return list_templates()


@router.get("/export-presets", response_model=list[ExportPresetRead])
def get_export_presets():
    return list_presets()
