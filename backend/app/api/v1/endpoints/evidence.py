"""
app/api/v1/endpoints/evidence.py
REST API endpoints for Incident Evidence Subsystem.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ....core.errors import OperixException
from ....models.enums import EvidenceKind
from ....schemas.common import APIResponse, APIResponseMeta
from ...ai_deps import get_evidence_service_dep
from ...deps import AuthenticatedUser, get_current_factory_id, get_current_user_context, get_tenant_db

router = APIRouter(prefix="/evidence", tags=["Incident Evidence"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EvidenceUploadJsonIn(BaseModel):
    event_id: UUID = Field(..., description="Target Event UUID")
    kind: str = Field(default="snapshot", description="'snapshot' or 'clip'")
    file_base64: str = Field(..., description="Base64-encoded file bytes")
    content_type: str = Field(default="image/jpeg", description="MIME content type (image/jpeg, video/mp4, etc.)")
    duration_s: Optional[float] = Field(default=None, description="Clip duration in seconds")
    captured_at: Optional[datetime] = Field(default=None, description="Capture timestamp (UTC)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Incident Evidence",
    description="Upload and cryptographically hash an evidence snapshot or video clip (JSON Base64 or binary).",
)
async def upload_evidence(
    payload: EvidenceUploadJsonIn,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    evidence_svc: Any = Depends(get_evidence_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Upload new evidence file with SHA-256 hash calculation."""
    from incident_evidence.schemas import EvidenceKind as Ek, EvidenceUploadRequest

    norm_kind = Ek(payload.kind.lower())
    cap_time = payload.captured_at or datetime.now(timezone.utc)

    try:
        file_bytes = base64.b64decode(payload.file_base64)
    except Exception as b64_err:
        raise OperixException(
            message=f"Invalid Base64 payload: {b64_err}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_BASE64",
        )

    upload_req = EvidenceUploadRequest(
        factory_id=user.factory_id,
        event_id=payload.event_id,
        kind=norm_kind,
        duration_s=payload.duration_s,
        captured_at=cap_time,
    )

    record = evidence_svc.upload(
        conn=db,
        request=upload_req,
        file_bytes=file_bytes,
        content_type=payload.content_type,
    )

    rec_dict = record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)
    return APIResponse(
        status="success",
        data=rec_dict,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "",
    response_model=APIResponse[Any],
    status_code=status.HTTP_200_OK,
    summary="List Evidence Records",
    description="List evidence records filtered by event_id, incident_id, or paginated by factory.",
)
def list_evidence(
    event_id: Optional[UUID] = Query(default=None, description="Filter by event UUID"),
    incident_id: Optional[UUID] = Query(default=None, description="Filter by incident UUID"),
    kind: Optional[str] = Query(default=None, description="Filter by kind ('snapshot' or 'clip')"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    evidence_svc: Any = Depends(get_evidence_service_dep),
) -> APIResponse[Any]:
    """List evidence files with tenant isolation."""
    from incident_evidence.schemas import EvidenceKind as Ek
    ek = Ek(kind.lower()) if kind else None

    if event_id is not None:
        records = evidence_svc.list_by_event(conn=db, event_id=event_id, factory_id=user.factory_id, kind=ek)
        serialized = [r.model_dump(mode="json") if hasattr(r, "model_dump") else dict(r) for r in records]
        data = serialized
    elif incident_id is not None:
        records = evidence_svc.list_by_incident(conn=db, incident_id=incident_id, factory_id=user.factory_id, kind=ek)
        serialized = [r.model_dump(mode="json") if hasattr(r, "model_dump") else dict(r) for r in records]
        data = serialized
    else:
        page_res = evidence_svc.list_by_factory(conn=db, factory_id=user.factory_id, kind=ek, page=page, page_size=page_size)
        data = page_res.model_dump(mode="json") if hasattr(page_res, "model_dump") else dict(page_res)

    return APIResponse(
        status="success",
        data=data,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{evidence_id}",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Evidence Metadata",
    description="Retrieve metadata for a specific evidence record.",
)
def get_evidence_metadata(
    evidence_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    evidence_svc: Any = Depends(get_evidence_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get metadata for an evidence record."""
    meta = evidence_svc.get_metadata(conn=db, evidence_id=evidence_id, factory_id=user.factory_id)
    meta_dict = meta.model_dump(mode="json") if hasattr(meta, "model_dump") else dict(meta)
    return APIResponse(
        status="success",
        data=meta_dict,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{evidence_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Evidence File",
    description="Download raw bytes of an evidence snapshot or clip.",
)
def download_evidence(
    evidence_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    evidence_svc: Any = Depends(get_evidence_service_dep),
):
    """Download evidence binary payload with factory verification."""
    file_bytes, record = evidence_svc.download(conn=db, evidence_id=evidence_id, factory_id=user.factory_id)
    storage_key = getattr(record, "storage_key", f"evidence_{evidence_id}")
    filename = storage_key.split("/")[-1]
    content_type = getattr(record, "content_type", "application/octet-stream")

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{evidence_id}/verify-integrity",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Verify Evidence Integrity",
    description="Re-calculate SHA-256 hash from physical disk file and compare against database checksum.",
)
def verify_evidence_integrity(
    evidence_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    evidence_svc: Any = Depends(get_evidence_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Cryptographically verify evidence file on disk."""
    res = evidence_svc.verify_integrity(conn=db, evidence_id=evidence_id, factory_id=user.factory_id)
    res_dict = res.model_dump(mode="json") if hasattr(res, "model_dump") else dict(res)
    return APIResponse(
        status="success",
        data=res_dict,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
