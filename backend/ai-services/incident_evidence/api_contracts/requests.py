"""
incident_evidence/api_contracts/requests.py
Request model contracts for the Incident Evidence API.

Endpoints covered:
  POST  /api/v1/evidence                   — EvidenceUploadRequest (re-exported)
  GET   /api/v1/evidence                   — EvidenceListQueryParams (re-exported)
  GET   /api/v1/evidence/{id}              — path param only
  GET   /api/v1/evidence/{id}/download     — path param only
  GET   /api/v1/incidents/{id}/evidence    — IncidentEvidenceQueryParams
  GET   /api/v1/evidence/{id}/verify       — path param only

Usage (FastAPI integration by Seif):
    from incident_evidence.api_contracts.requests import (
        EvidenceUploadMetadata,
        EvidenceListQueryParams,
        IncidentEvidenceQueryParams,
    )
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..schemas import EvidenceKind, EvidenceUploadRequest, EvidenceListQueryParams  # noqa: F401


class EvidenceUploadMetadata(BaseModel):
    """
    JSON metadata submitted alongside the binary file for POST /api/v1/evidence.

    In FastAPI, Seif will combine this with UploadFile:
        async def upload_evidence(
            meta: EvidenceUploadMetadata = Depends(),
            file: UploadFile = File(...),
        ):
    """
    factory_id: UUID = Field(description="Factory that owns this evidence.")
    event_id: UUID = Field(description="Event this evidence belongs to.")
    captured_at: Optional[datetime] = Field(
        default=None,
        description="When the evidence was captured (ISO-8601). Defaults to server time.",
    )
    duration_s: Optional[float] = Field(
        default=None,
        description="Duration in seconds (applicable to video/audio).",
        ge=0,
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiry timestamp. After this, the file may be purged.",
    )

    def to_upload_request(self) -> EvidenceUploadRequest:
        """Convert to the internal EvidenceUploadRequest schema."""
        from datetime import timezone
        return EvidenceUploadRequest(
            factory_id=self.factory_id,
            event_id=self.event_id,
            captured_at=self.captured_at or datetime.now(tz=timezone.utc),
            duration_s=self.duration_s,
            expires_at=self.expires_at,
        )


class IncidentEvidenceQueryParams(BaseModel):
    """
    Query parameters for GET /api/v1/incidents/{incident_id}/evidence.
    """
    factory_id: UUID = Field(description="Factory scope (required for security boundary).")
    kind: Optional[EvidenceKind] = Field(
        default=None,
        description="Filter by evidence kind (image, video, audio).",
    )
