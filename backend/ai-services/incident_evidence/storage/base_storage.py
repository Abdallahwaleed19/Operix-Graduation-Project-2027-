"""
incident_evidence/storage/base_storage.py
Abstract base class defining the storage interface for evidence files.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Optional
from uuid import UUID


class BaseStorage(ABC):
    """
    Abstract storage backend for evidence files.

    Implementations:
      - LocalStorage  (default, filesystem-based)
      - Future: S3Storage, AzureBlobStorage, GCSStorage
    """

    @abstractmethod
    def generate_key(
        self,
        factory_id: UUID,
        event_id: UUID,
        evidence_id: UUID,
        extension: str,
    ) -> str:
        """
        Generate a deterministic storage key (relative path / object key).

        The key must be collision-resistant, URL-safe, and must NOT expose
        internal path traversal sequences.

        Args:
            factory_id: The owning factory UUID.
            event_id:   The parent event UUID.
            evidence_id: The new evidence UUID.
            extension:  File extension including the dot, e.g. ".jpg".

        Returns:
            A string key that uniquely identifies the stored object.
        """

    @abstractmethod
    def save(self, key: str, data: bytes) -> int:
        """
        Persist raw bytes under the given key.

        Returns the number of bytes written.
        Raises StorageError on failure.
        """

    @abstractmethod
    def load(self, key: str) -> bytes:
        """
        Load and return the raw bytes stored under key.

        Raises StorageError if the key does not exist.
        """

    @abstractmethod
    def stream(self, key: str, chunk_size: int = 65536) -> Iterator[bytes]:
        """
        Yield the stored content in chunks (for streaming downloads).

        Raises StorageError if the key does not exist.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Remove the stored object.

        Raises StorageError on failure.  Should be idempotent if the key
        is already absent.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if an object exists for the given key."""

    @abstractmethod
    def size(self, key: str) -> int:
        """Return the byte-size of the stored object.  Raises StorageError if absent."""

    def absolute_path(self, key: str) -> Optional[Path]:  # noqa: D401
        """
        Return the absolute filesystem path for the key, if applicable.

        Default implementation returns None.  LocalStorage overrides this.
        """
        return None
