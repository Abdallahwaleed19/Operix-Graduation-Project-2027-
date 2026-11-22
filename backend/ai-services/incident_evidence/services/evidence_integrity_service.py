"""
incident_evidence/services/evidence_integrity_service.py
SHA-256 integrity verification for stored evidence files.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.engine import Connection

from ..exceptions import EvidenceNotFoundError, StorageError
from ..repositories import EvidenceRepository
from ..schemas import IntegrityVerificationResult
from ..storage.local_storage import LocalStorage


class EvidenceIntegrityService:
    """
    Re-computes the SHA-256 of a stored evidence file and compares it
    against the hash recorded in the evidence_files table at upload time.
    """

    def __init__(self, storage: LocalStorage) -> None:
        self._storage = storage

    def verify(
        self,
        conn: Connection,
        evidence_id: UUID,
        factory_id: UUID,
    ) -> IntegrityVerificationResult:
        """
        Verify the integrity of a stored evidence file.

        Returns an IntegrityVerificationResult with:
          - stored_sha256:   the hash saved in the DB at upload
          - computed_sha256: the hash re-computed from the file on disk
          - integrity_ok:    True if they match (or if no stored hash is available)
          - message:         human-readable status

        Does NOT raise on hash mismatch — the result model carries the status.
        Raises EvidenceNotFoundError if the record or file is missing.
        """
        repo = EvidenceRepository(conn)
        record = repo.get_by_id(evidence_id, factory_id)

        storage_key = record.storage_key
        if not self._storage.exists(storage_key):
            raise StorageError(
                f"Evidence file not found on disk for key: {storage_key}"
            )

        # Stream file and compute SHA-256 without loading everything into RAM
        hasher = hashlib.sha256()
        try:
            for chunk in self._storage.stream(storage_key):
                hasher.update(chunk)
        except StorageError:
            raise

        computed = hasher.hexdigest()
        stored = record.sha256

        if stored is None:
            integrity_ok = True
            message = (
                "No stored SHA-256 hash found in DB record. "
                "Integrity could not be verified; computed hash recorded above."
            )
        elif computed == stored:
            integrity_ok = True
            message = "Integrity verified: SHA-256 matches."
        else:
            integrity_ok = False
            message = (
                f"INTEGRITY FAILURE: computed SHA-256 ({computed[:16]}…) "
                f"does NOT match stored hash ({stored[:16]}…). "
                "The file may be corrupted or tampered with."
            )

        return IntegrityVerificationResult(
            evidence_id=evidence_id,
            storage_key=storage_key,
            stored_sha256=stored,
            computed_sha256=computed,
            integrity_ok=integrity_ok,
            message=message,
            verified_at=datetime.now(tz=timezone.utc),
        )
