"""
incident_evidence/exceptions.py
Custom exception hierarchy for the Incident Evidence module.
"""
from __future__ import annotations


class EvidenceBaseException(Exception):
    """Root exception for all evidence module errors."""


class EvidenceNotFoundError(EvidenceBaseException):
    """Raised when a requested evidence record or file does not exist."""


class InvalidEvidenceTypeError(EvidenceBaseException):
    """Raised when an unsupported evidence kind is provided."""


class FileSizeLimitError(EvidenceBaseException):
    """Raised when an uploaded file exceeds the allowed size limit."""


class InvalidMimeTypeError(EvidenceBaseException):
    """Raised when a file's MIME type is not in the allowed set."""


class StorageError(EvidenceBaseException):
    """Raised on file-system storage read/write failures."""


class IntegrityVerificationError(EvidenceBaseException):
    """Raised when a stored file's SHA-256 hash does not match the DB record."""


class EvidenceTransactionError(EvidenceBaseException):
    """Raised when a DB-transaction write fails (e.g., during upload atomicity)."""


class EvidenceExpiredError(EvidenceBaseException):
    """Raised when evidence has passed its expiry date and is no longer available."""


class EvidencePurgedError(EvidenceBaseException):
    """Raised when evidence has been marked as purged and the file no longer exists."""
