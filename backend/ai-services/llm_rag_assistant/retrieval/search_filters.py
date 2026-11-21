"""
retrieval/search_filters.py
Helper builders for search filters.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from ..schemas.contracts import DocumentSourceType, RetrievalFilter


def build_filter(
    factory_id: Optional[UUID] = None,
    department_id: Optional[UUID] = None,
    source_types: Optional[List[DocumentSourceType]] = None,
    top_k: int = 5,
    min_similarity: float = 0.60,
) -> RetrievalFilter:
    """
    Construct validated RetrievalFilter.
    """
    return RetrievalFilter(
        factory_id=factory_id,
        department_id=department_id,
        source_types=source_types,
        top_k=top_k,
        min_similarity=min_similarity,
    )
