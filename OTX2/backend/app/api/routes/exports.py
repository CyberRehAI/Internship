from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models.schemas import ExportRequest, ExportResponse
from app.services.export_service import ExportService

router = APIRouter(prefix="/api", tags=["exports"])


def get_export_service() -> ExportService:
    settings = get_settings()
    return ExportService(Path("exports"), settings.export_retention_hours)


@router.post("/iocs/export", response_model=ExportResponse)
def export_iocs(payload: ExportRequest, service: ExportService = Depends(get_export_service)) -> ExportResponse:
    result = service.export([item.model_dump() for item in payload.iocs], payload.mode, payload.format)
    return ExportResponse(**result)


@router.get("/exports/{export_id}/download")
def download_export(export_id: str, service: ExportService = Depends(get_export_service)) -> FileResponse:
    target = service.get_export_path(export_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
    return FileResponse(path=target, filename=target.name)
