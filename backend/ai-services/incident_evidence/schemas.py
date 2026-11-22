"""
incident_evidence/schemas.py
Pydantic v2 data models and enums for the Incident Evidence module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EvidenceKind(str, Enum):
    """
    Allowed values for evidence_files.kind (VARCHAR 8).
    Each value must be ≤ 8 characters to fit the column constraint.
    """
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


# ---------------------------------------------------------------------------
# DB-mapped model
# ---------------------------------------------------------------------------

class EvidenceFileRecord(BaseModel):
    """
    Mirrors the evidence_files table structure.

    Column mapping (verified via SQLAlchemy inspector):
      id           UUID PK
      factory_id   UUID FK → factories.id
      event_id     UUID composite FK → events.(factory_id, id)
      kind         VARCHAR(8)
      storage_key  TEXT UNIQUE
      content_type VARCHAR(60)
      size_bytes   BIGINT
      sha256       CHAR(64) nullable
      duration_s   NUMERIC(6,2) nullable
      captured_at  TIMESTAMP
      expires_at   TIMESTAMP nullable
      purged_at    TIMESTAMP nullable
      created_at   TIMESTAMP
    """
    id: UUID
    factory_id: UUID
    event_id: UUID
    kind: EvidenceKind
    storage_key: str
    content_type: str
    size_bytes: int
    sha256: Optional[str] = None
    duration_s: Optional[float] = None
    captured_at: datetime
    expires_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(tz=timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def is_purged(self) -> bool:
        return self.purged_at is not None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EvidenceUploadRequest(BaseModel):
    """
    Metadata provided alongside a file upload.

    The actual file bytes come separately (as multipart/form-data in HTTP).
    This model represents the JSON metadata portion.
    """
    factory_id: UUID
    event_id: UUID
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="When the evidence was captured (defaults to now).",
    )
    duration_s: Optional[float] = Field(
        default=None,
        description="Duration in seconds, applicable to video/audio evidence.",
        ge=0,
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiry timestamp after which the file may be purged.",
    )

    @field_validator("duration_s")
    @classmethod
    def duration_max(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 999_999.99:
            raise ValueError("duration_s exceeds NUMERIC(6,2) max (999999.99).")
        return v


class EvidenceListQueryParams(BaseModel):
    """Query parameters for the paginated evidence list endpoint."""
    factory_id: Optional[UUID] = None
    kind: Optional[EvidenceKind] = None
    event_id: Optional[UUID] = None
    incident_id: Optional[UUID] = None
    captured_after: Optional[datetime] = None
    captured_before: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class EvidenceMetadataResponse(BaseModel):
    """
    Returned for GET /api/v1/evidence/{id} and POST /api/v1/evidence.

    Extends EvidenceFileRecord with computed convenience fields.
    """
    id: UUID
    factory_id: UUID
    event_id: UUID
    kind: EvidenceKind
    storage_key: str
    content_type: str
    size_bytes: int
    sha256: Optional[str] = None
    duration_s: Optional[float] = None
    captured_at: datetime
    expires_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    created_at: datetime
    is_expired: bool = False
    is_purged: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_record(cls, record: EvidenceFileRecord) -> "EvidenceMetadataResponse":
        return cls(
            **record.model_dump(),
            is_expired=record.is_expired,
            is_purged=record.is_purged,
        )


class IntegrityVerificationResult(BaseModel):
    """Returned by GET /api/v1/evidence/{id}/verify."""
    evidence_id: UUID
    storage_key: str
    stored_sha256: Optional[str]
    computed_sha256: Optional[str]
    integrity_ok: bool
    message: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class EvidenceListResponse(BaseModel):
    """Paginated list of evidence records."""
    success: bool = True
    total: int
    page: int = 1
    page_size: int = 20
    data: List[EvidenceMetadataResponse]


class EvidenceUploadResponse(BaseModel):
    """Returned immediately after a successful evidence upload."""
    success: bool = True
    message: str = "Evidence uploaded and recorded successfully."
    data: EvidenceMetadataResponse
