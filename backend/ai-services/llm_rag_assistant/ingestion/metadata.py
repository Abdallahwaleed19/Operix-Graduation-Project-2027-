"""
ingestion/metadata.py
Metadata generation, normalization, and deduplication hashing.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional
from uuid import UUID

from ..schemas.contracts import ChunkMetadata, DocumentSourceType


def compute_chunk_hash(content: str, source_id: str, page_number: Optional[int] = None) -> str:
    """
    Generate deterministic SHA-256 hash to detect duplicate chunks.
    """
    payload = f"{source_id}:{page_number or 0}:{content.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def create_metadata(
    source_id: str,
    source_title: str,
    source_type: DocumentSourceType,
    content: str,
    factory_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    page_number: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> ChunkMetadata:
    """
    Construct validated ChunkMetadata with deterministic chunk_id.
    """
    chunk_id = f"chk_{compute_chunk_hash(content, source_id, page_number)}"
    return ChunkMetadata(
        chunk_id=chunk_id,
        source_id=source_id,
        source_title=source_title,
        source_type=source_type,
        factory_id=factory_id,
        department_id=department_id,
        page_number=page_number,
        extra=extra or {},
    )
