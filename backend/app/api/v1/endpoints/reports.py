"""
app/api/v1/endpoints/reports.py
REST API endpoints for Reports Generation Subsystem.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ....core.errors import ResourceNotFoundException, TenantAccessDeniedException
from ....schemas.common import APIResponse, APIResponseMeta
from ...ai_deps import get_reports_service_dep, get_reports_storage_path
from ...deps import AuthenticatedUser, get_current_factory_id, get_current_user_context, get_tenant_db

router = APIRouter(prefix="/reports", tags=["Reports Generation"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportGenerateIn(BaseModel):
    report_type: str = Field(
        ...,
        description="Type of report: 'workforce', 'incident', 'camera_coverage', 'comprehensive_safety'",
    )
    format: str = Field(
        default="pdf",
        description="Artifact format: 'pdf' or 'excel'",
    )
    date_from: Optional[date] = Field(default=None, description="Start date for reporting window")
    date_to: Optional[date] = Field(default=None, description="End date for reporting window")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Safety Report",
    description="Generate a PDF or Excel report artifact for the tenant factory.",
)
def generate_report(
    payload: ReportGenerateIn,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    reports_svc: Any = Depends(get_reports_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Generate domain safety report artifact."""
    meta = reports_svc.generate_report(
        report_type=payload.report_type,
        format=payload.format,
        factory_id=user.factory_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    meta_dict = meta.model_dump(mode="json") if hasattr(meta, "model_dump") else dict(meta)
    return APIResponse(
        status="success",
        data=meta_dict,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "",
    response_model=APIResponse[List[Dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="List Generated Reports",
    description="List all available generated report artifacts for the tenant factory.",
)
def list_reports(
    user: AuthenticatedUser = Depends(get_current_user_context),
    reports_svc: Any = Depends(get_reports_service_dep),
) -> APIResponse[List[Dict[str, Any]]]:
    """List available report artifacts."""
    reports = reports_svc.list_reports(factory_id=user.factory_id)
    serialized = [r.model_dump(mode="json") if hasattr(r, "model_dump") else dict(r) for r in reports]
    return APIResponse(
        status="success",
        data=serialized,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{report_id}",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Report Metadata",
    description="Retrieve metadata for a specific generated report.",
)
def get_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user_context),
    reports_svc: Any = Depends(get_reports_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get metadata for a generated report."""
    meta = reports_svc.get_report(report_id, factory_id=user.factory_id)

    # Multi-tenant boundary verification
    if meta.factory_id and meta.factory_id != user.factory_id:
        raise TenantAccessDeniedException("Access denied: Report belongs to another factory.")

    meta_dict = meta.model_dump(mode="json") if hasattr(meta, "model_dump") else dict(meta)
    return APIResponse(
        status="success",
        data=meta_dict,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{report_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Report Artifact",
    description="Download the physical PDF or Excel report artifact.",
)
def download_report(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user_context),
    reports_svc: Any = Depends(get_reports_service_dep),
):
    """Download physical report file with path traversal verification."""
    meta = reports_svc.get_report(report_id, factory_id=user.factory_id)

    # Multi-tenant boundary check
    if meta.factory_id and meta.factory_id != user.factory_id:
        raise TenantAccessDeniedException("Access denied: Report belongs to another factory.")

    file_path = reports_svc.get_report_file_path(report_id, factory_id=user.factory_id)
    resolved_path = Path(file_path).resolve()
    base_storage = get_reports_storage_path().resolve()

    # Prevent path traversal attacks
    if not str(resolved_path).startswith(str(base_storage)):
        raise TenantAccessDeniedException("Path traversal attempt detected.")

    if not resolved_path.exists():
        raise ResourceNotFoundException("report_file", f"File '{resolved_path.name}' not found on storage.")

    media_type = getattr(meta, "mime_type", "application/octet-stream")
    file_name = getattr(meta, "file_name", resolved_path.name)
    return FileResponse(
        path=str(resolved_path),
        filename=file_name,
        media_type=media_type,
    )
