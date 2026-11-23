"""
incident_evidence/storage/local_storage.py
Filesystem-backed storage implementation.

Security hardening:
  - UUID-based filenames; no user-supplied file names are used for the
    actual on-disk path.
  - Path traversal prevention via strict prefix check on the resolved path.
  - Atomic write via a temporary file + rename (os.replace).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterator, Optional
from uuid import UUID

from ..exceptions import StorageError
from .base_storage import BaseStorage


class LocalStorage(BaseStorage):
    """
    Stores evidence files on the local filesystem under a configurable root.

    Directory layout:
        <root>/<factory_id>/<event_id>/<evidence_id><ext>

    Example:
        storage/evidence/aaaaaaaa-0001-0001-0001-000000000001/
                        bbbbbbbb-0002-0002-0002-000000000002/
                        cccccccc-0003-0003-0003-000000000003.jpg
    """

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_resolve(self, key: str) -> Path:
        """
        Resolve key to an absolute path and verify it stays under _root.

        Raises StorageError if the resolved path escapes the root (path traversal).
        """
        # key is a relative POSIX-style path, e.g.
        # "aaaaaaaa-0001-0001-0001-000000000001/event_id/evidence_id.jpg"
        candidate = (self._root / key).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError:
            raise StorageError(
                f"Path traversal detected: key '{key}' resolves outside storage root."
            )
        return candidate

    # ------------------------------------------------------------------
    # BaseStorage implementation
    # ------------------------------------------------------------------

    def generate_key(
        self,
        factory_id: UUID,
        event_id: UUID,
        evidence_id: UUID,
        extension: str,
    ) -> str:
        """
        Return a relative key string matching the PostgreSQL check constraint:
        CHECK (storage_key LIKE 'f/' || factory_id::text || '/%')

        Pattern: "f/{factory_id}/{event_id}/{evidence_id}{ext}"
        """
        ext = extension if extension.startswith(".") else f".{extension}"
        return f"f/{factory_id}/{event_id}/{evidence_id}{ext}"

    def save(self, key: str, data: bytes) -> int:
        """Write bytes atomically.  Returns bytes written."""
        dest = self._safe_resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then atomically replace
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dest.parent, prefix=".tmp_")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                os.replace(tmp_path, dest)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"Failed to save evidence file [{key}]: {exc}") from exc
        return len(data)

    def load(self, key: str) -> bytes:
        """Read and return all bytes for the given key."""
        path = self._safe_resolve(key)
        if not path.exists():
            raise StorageError(f"Evidence file not found: {key}")
        try:
            return path.read_bytes()
        except Exception as exc:
            raise StorageError(f"Failed to load evidence file [{key}]: {exc}") from exc

    def stream(self, key: str, chunk_size: int = 65536) -> Iterator[bytes]:
        """Yield chunks of the stored file."""
        path = self._safe_resolve(key)
        if not path.exists():
            raise StorageError(f"Evidence file not found for streaming: {key}")
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"Failed to stream evidence file [{key}]: {exc}") from exc

    def delete(self, key: str) -> None:
        """Remove the file (idempotent)."""
        path = self._safe_resolve(key)
        try:
            if path.exists():
                path.unlink()
        except Exception as exc:
            raise StorageError(f"Failed to delete evidence file [{key}]: {exc}") from exc

    def exists(self, key: str) -> bool:
        """Return True if the file exists."""
        try:
            path = self._safe_resolve(key)
            return path.exists()
        except StorageError:
            return False

    def size(self, key: str) -> int:
        """Return file size in bytes."""
        path = self._safe_resolve(key)
        if not path.exists():
            raise StorageError(f"Evidence file not found: {key}")
        return path.stat().st_size

    def absolute_path(self, key: str) -> Optional[Path]:
        """Return the absolute path for the key."""
        try:
            return self._safe_resolve(key)
        except StorageError:
            return None
