"""
incident_evidence/services/evidence_retrieval_service.py
Retrieval operations for evidence records and their binary content.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional
from uuid import UUID

from sqlalchemy.engine import Connection

from ..exceptions import EvidenceExpiredError, EvidenceNotFoundError, EvidencePurgedError
from ..repositories import EvidenceRepository
from ..schemas import (
    EvidenceFileRecord,
    EvidenceKind,
    EvidenceListResponse,
    EvidenceMetadataResponse,
)
from ..storage.local_storage import LocalStorage


class EvidenceRetrievalService:
    """
    Provides read access to evidence records and their binary files.
    """

    def __init__(self, storage: LocalStorage) -> None:
        self._storage = storage

    # ------------------------------------------------------------------
    # Single record
    # ------------------------------------------------------------------

    def get_metadata(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> EvidenceMetadataResponse:
        """Return metadata for a single evidence file."""
        repo = EvidenceRepository(conn)
        record = repo.get_by_id(evidence_id, factory_id)
        return EvidenceMetadataResponse.from_record(record)

    # ------------------------------------------------------------------
    # By event
    # ------------------------------------------------------------------

    def list_by_event(
        self,
        conn: Connection,
        event_id: UUID,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
    ) -> List[EvidenceMetadataResponse]:
        """Return all evidence records for a specific event."""
        repo = EvidenceRepository(conn)
        records = repo.get_by_event_id(event_id, factory_id, kind=kind)
        return [EvidenceMetadataResponse.from_record(r) for r in records]

    # ------------------------------------------------------------------
    # By incident (JOIN through events)
    # ------------------------------------------------------------------

    def list_by_incident(
        self,
        conn: Connection,
        incident_id: UUID,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
    ) -> List[EvidenceMetadataResponse]:
        """
        Return all evidence linked to an incident.

        Uses the verified DB relationship chain:
          incidents.id ← events.incident_id ← evidence_files.(factory_id, event_id)
        """
        repo = EvidenceRepository(conn)
        records = repo.get_by_incident_id(incident_id, factory_id, kind=kind)
        return [EvidenceMetadataResponse.from_record(r) for r in records]

    # ------------------------------------------------------------------
    # Paginated factory-wide list
    # ------------------------------------------------------------------

    def list_by_factory(
        self,
        conn: Connection,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
        captured_after: Optional[datetime] = None,
        captured_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> EvidenceListResponse:
        """Return a paginated list of evidence for a factory."""
        repo = EvidenceRepository(conn)
        records, total = repo.list_by_factory(
            factory_id=factory_id,
            kind=kind,
            captured_after=captured_after,
            captured_before=captured_before,
            page=page,
            page_size=page_size,
        )
        return EvidenceListResponse(
            total=total,
            page=page,
            page_size=page_size,
            data=[EvidenceMetadataResponse.from_record(r) for r in records],
        )

    # ------------------------------------------------------------------
    # Binary download
    # ------------------------------------------------------------------

    def _check_downloadable(self, record: EvidenceFileRecord) -> None:
        """Raise if the record is purged or expired."""
        if record.is_purged:
            raise EvidencePurgedError(
                f"Evidence {record.id} has been purged and is no longer available."
            )
        if record.is_expired:
            raise EvidenceExpiredError(
                f"Evidence {record.id} has expired and cannot be downloaded."
            )

    def download(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> tuple[bytes, EvidenceFileRecord]:
        """
        Return (raw_bytes, record) for the requested evidence.

        Raises EvidencePurgedError or EvidenceExpiredError if unavailable.
        Raises EvidenceNotFoundError if the record or file does not exist.
        """
        repo = EvidenceRepository(conn)
        record = repo.get_by_id(evidence_id, factory_id)
        self._check_downloadable(record)
        raw = self._storage.load(record.storage_key)
        return raw, record

    def stream(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
        chunk_size: int = 65536,
    ) -> tuple[Iterator[bytes], EvidenceFileRecord]:
        """
        Return (byte_iterator, record) for streaming download.

        Raises EvidencePurgedError or EvidenceExpiredError if unavailable.
        """
        repo = EvidenceRepository(conn)
        record = repo.get_by_id(evidence_id, factory_id)
        self._check_downloadable(record)
        byte_iter = self._storage.stream(record.storage_key, chunk_size=chunk_size)
        return byte_iter, record

    def get_absolute_path(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> Optional[Path]:
        """
        Return the absolute filesystem path for the evidence file, if stored locally.

        Used by Seif's FastAPI layer to build a FileResponse.
        Returns None if the file is not found on disk.
        """
        repo = EvidenceRepository(conn)
        record = repo.get_by_id(evidence_id, factory_id)
        self._check_downloadable(record)
        return self._storage.absolute_path(record.storage_key)
