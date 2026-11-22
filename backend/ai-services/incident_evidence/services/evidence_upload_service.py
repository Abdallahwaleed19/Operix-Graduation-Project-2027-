"""
incident_evidence/services/evidence_upload_service.py
Validates, stores, and records a new evidence file atomically.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.engine import Connection

from ..config import (
    ALLOWED_MIME_TYPES,
    EVIDENCE_STORAGE_DIR,
    MAX_EVIDENCE_SIZE_BYTES,
    MIME_TO_KIND,
)
from ..exceptions import (
    EvidenceTransactionError,
    FileSizeLimitError,
    InvalidMimeTypeError,
    StorageError,
)
from ..repositories import EvidenceRepository
from ..schemas import EvidenceFileRecord, EvidenceKind, EvidenceUploadRequest
from ..storage.local_storage import LocalStorage


def _guess_extension(content_type: str) -> str:
    _map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/mpeg": ".mpeg",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/webm": ".webm",
    }
    return _map.get(content_type, ".bin")


class EvidenceUploadService:
    """
    Handles end-to-end evidence upload:
      1. Validate MIME type and file size.
      2. Compute SHA-256 while reading bytes.
      3. Save file to storage atomically (with rollback on DB failure).
      4. Insert evidence_files record.
    """

    def __init__(
        self,
        storage: Optional[LocalStorage] = None,
        storage_dir: Optional[Path] = None,
    ) -> None:
        root = storage_dir or EVIDENCE_STORAGE_DIR
        self._storage = storage or LocalStorage(root)

    def upload(
        self,
        conn: Connection,
        request: EvidenceUploadRequest,
        file_bytes: bytes,
        content_type: str,
    ) -> EvidenceFileRecord:
        """
        Validate, store, and record evidence.

        Args:
            conn:         SQLAlchemy connection (caller manages transaction).
            request:      Upload metadata (factory_id, event_id, captured_at, …).
            file_bytes:   Raw bytes of the uploaded file.
            content_type: Declared MIME type (e.g. "image/jpeg").

        Returns:
            The newly created EvidenceFileRecord.

        Raises:
            InvalidMimeTypeError  if content_type is not in ALLOWED_MIME_TYPES.
            FileSizeLimitError    if len(file_bytes) > MAX_EVIDENCE_SIZE_BYTES.
            StorageError          if the filesystem write fails.
            EvidenceTransactionError if the DB INSERT fails.
        """
        # 1. MIME type validation
        if content_type not in ALLOWED_MIME_TYPES:
            raise InvalidMimeTypeError(
                f"MIME type '{content_type}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_MIME_TYPES)}"
            )

        # 2. Size validation
        size_bytes = len(file_bytes)
        if size_bytes > MAX_EVIDENCE_SIZE_BYTES:
            from ..config import MAX_EVIDENCE_SIZE_MB
            raise FileSizeLimitError(
                f"File size {size_bytes / 1024 / 1024:.1f} MB exceeds "
                f"maximum allowed {MAX_EVIDENCE_SIZE_MB} MB."
            )

        # 3. Compute SHA-256
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # 4. Determine kind
        kind = EvidenceKind(MIME_TO_KIND[content_type])

        # 5. Generate IDs and storage key
        evidence_id = uuid.uuid4()
        extension = _guess_extension(content_type)
        storage_key = self._storage.generate_key(
            factory_id=request.factory_id,
            event_id=request.event_id,
            evidence_id=evidence_id,
            extension=extension,
        )

        # 6. Save file to storage
        try:
            self._storage.save(storage_key, file_bytes)
        except StorageError:
            raise

        # 7. Insert DB record (rollback file on failure)
        repo = EvidenceRepository(conn)
        try:
            record = repo.create_record(
                factory_id=request.factory_id,
                event_id=request.event_id,
                kind=kind,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size_bytes,
                captured_at=request.captured_at or datetime.now(tz=timezone.utc),
                sha256=sha256,
                duration_s=request.duration_s,
                expires_at=request.expires_at,
            )
        except EvidenceTransactionError:
            # Rollback file from storage
            try:
                self._storage.delete(storage_key)
            except StorageError:
                pass  # Best-effort rollback
            raise

        return record
