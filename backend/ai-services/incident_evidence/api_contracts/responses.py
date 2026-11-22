"""
incident_evidence/api_contracts/responses.py
Response contracts for the Incident Evidence API.

Endpoints and their response models:
  POST  /api/v1/evidence                   → EvidenceUploadResponse
  GET   /api/v1/evidence                   → EvidenceListResponse
  GET   /api/v1/evidence/{id}              → EvidenceSingleResponse
  GET   /api/v1/evidence/{id}/download     → binary stream (FastAPI FileResponse)
  GET   /api/v1/incidents/{id}/evidence    → EvidenceListResponse
  GET   /api/v1/evidence/{id}/verify       → IntegrityVerificationResponse

Example JSON — EvidenceUploadResponse:
  {
    "success": true,
    "message": "Evidence uploaded and recorded successfully.",
    "data": {
      "id": "cccccccc-0003-0003-0003-000000000003",
      "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
      "event_id": "bbbbbbbb-0001-0001-0001-000000000001",
      "kind": "image",
      "storage_key": "aaaaaaaa-.../bbbbbbbb-.../cccccccc-....jpg",
      "content_type": "image/jpeg",
      "size_bytes": 204800,
      "sha256": "e3b0c44298fc1c149afb...",
      "duration_s": null,
      "captured_at": "2027-01-15T10:00:00+00:00",
      "expires_at": null,
      "purged_at": null,
      "created_at": "2027-01-15T10:00:01+00:00",
      "is_expired": false,
      "is_purged": false
    }
  }
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..schemas import (  # noqa: F401 — re-export for Seif's FastAPI layer
    EvidenceListResponse,
    EvidenceMetadataResponse,
    EvidenceUploadResponse,
    IntegrityVerificationResult,
)


class EvidenceSingleResponse(BaseModel):
    """Envelope for GET /api/v1/evidence/{id}."""
    success: bool = True
    data: EvidenceMetadataResponse


class IntegrityVerificationResponse(BaseModel):
    """Envelope for GET /api/v1/evidence/{id}/verify."""
    success: bool = True
    data: IntegrityVerificationResult


class EvidenceDownloadInfo(BaseModel):
    """
    Metadata returned before Seif's FastAPI layer streams the binary.

    Seif should use `file_path` to build a `FileResponse`:
        return FileResponse(
            path=resp.file_path,
            media_type=resp.mime_type,
            filename=resp.suggested_filename,
        )
    """
    evidence_id: UUID
    storage_key: str
    file_path: str = Field(description="Absolute path on disk.")
    mime_type: str
    size_bytes: int
    suggested_filename: str

    model_config = {"json_schema_extra": {
        "example": {
            "evidence_id": "cccccccc-0003-0003-0003-000000000003",
            "storage_key": "aaaa.../bbbb.../cccc....jpg",
            "file_path": "/app/storage/evidence/aaaa.../bbbb.../cccc....jpg",
            "mime_type": "image/jpeg",
            "size_bytes": 204800,
            "suggested_filename": "evidence_cccccccc-0003.jpg",
        }
    }}


class EvidenceErrorResponse(BaseModel):
    """Standard error envelope for the evidence API."""
    success: bool = False
    error_code: str
    message: str
    detail: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "success": False,
            "error_code": "EVIDENCE_NOT_FOUND",
            "message": "Evidence cccccccc-0003-0003-0003-000000000003 not found.",
            "detail": None,
        }
    }}
