"""
incident_evidence/services/evidence_service.py
Facade combining upload, retrieval, and integrity services.

Usage:
    from incident_evidence.services.evidence_service import EvidenceService, get_evidence_service

    svc = get_evidence_service()
    record = svc.upload(conn, request, file_bytes, "image/jpeg")
    result = svc.verify_integrity(conn, record.id, factory_id)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.engine import Connection

from ..config import EVIDENCE_STORAGE_DIR
from ..schemas import (
    EvidenceKind,
    EvidenceListResponse,
    EvidenceMetadataResponse,
    EvidenceUploadRequest,
    EvidenceFileRecord,
    IntegrityVerificationResult,
)
from ..storage.local_storage import LocalStorage
from .evidence_integrity_service import EvidenceIntegrityService
from .evidence_retrieval_service import EvidenceRetrievalService
from .evidence_upload_service import EvidenceUploadService


class EvidenceService:
    """
    Top-level service facade for incident evidence management.

    Sub-services:
      - EvidenceUploadService    — validation, storage, DB record creation
      - EvidenceRetrievalService — read access to records and files
      - EvidenceIntegrityService — SHA-256 re-verification
    """

    def __init__(
        self,
        storage: Optional[LocalStorage] = None,
        storage_dir: Optional[Path] = None,
    ) -> None:
        root = storage_dir or EVIDENCE_STORAGE_DIR
        _storage = storage or LocalStorage(root)
        self._upload_svc = EvidenceUploadService(storage=_storage)
        self._retrieval_svc = EvidenceRetrievalService(storage=_storage)
        self._integrity_svc = EvidenceIntegrityService(storage=_storage)

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload(
        self,
        conn: Connection,
        request: EvidenceUploadRequest,
        file_bytes: bytes,
        content_type: str,
    ) -> EvidenceFileRecord:
        """Validate, store, and record a new evidence file."""
        return self._upload_svc.upload(conn, request, file_bytes, content_type)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_metadata(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> EvidenceMetadataResponse:
        """Get metadata for a single evidence record."""
        return self._retrieval_svc.get_metadata(conn, evidence_id, factory_id)

    def list_by_event(
        self,
        conn: Connection,
        event_id: UUID,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
    ):
        """List all evidence records for a specific event."""
        return self._retrieval_svc.list_by_event(conn, event_id, factory_id, kind=kind)

    def list_by_incident(
        self,
        conn: Connection,
        incident_id: UUID,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
    ):
        """List all evidence records linked to an incident (via events JOIN)."""
        return self._retrieval_svc.list_by_incident(conn, incident_id, factory_id, kind=kind)

    def list_by_factory(
        self,
        conn: Connection,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> EvidenceListResponse:
        """Return a paginated factory-wide evidence list."""
        return self._retrieval_svc.list_by_factory(
            conn, factory_id, kind=kind, page=page, page_size=page_size
        )

    def download(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> tuple[bytes, EvidenceFileRecord]:
        """Download raw bytes for an evidence file."""
        return self._retrieval_svc.download(conn, evidence_id, factory_id)

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def verify_integrity(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> IntegrityVerificationResult:
        """Re-compute SHA-256 and verify against the DB record."""
        return self._integrity_svc.verify(conn, evidence_id, factory_id)


# ---------------------------------------------------------------------------
# Singleton helper
# ---------------------------------------------------------------------------
_instance: Optional[EvidenceService] = None


def get_evidence_service(
    storage_dir: Optional[Path] = None,
) -> EvidenceService:
    """Return a module-level singleton EvidenceService."""
    global _instance
    if _instance is None:
        _instance = EvidenceService(storage_dir=storage_dir)
    return _instance
