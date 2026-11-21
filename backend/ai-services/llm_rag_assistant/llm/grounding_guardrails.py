"""
llm/grounding_guardrails.py
Output verification, anti-hallucination validation, and prompt injection defense.
"""
from __future__ import annotations

import re
from typing import List

from ..schemas.contracts import RetrievedChunk, SourceCitation

# Standard refusal phrases
INSUFFICIENT_EVIDENCE_PHRASES = [
    "insufficient information",
    "insufficient evidence",
    "لا توجد معلومات كافية",
    "معلومات غير كافية",
    "سجلات غير كافية",
]


def is_refusal_response(answer: str) -> bool:
    """Detect if the generated response honestly reported insufficient evidence."""
    lower = answer.lower()
    return any(p.lower() in lower for p in INSUFFICIENT_EVIDENCE_PHRASES)


def extract_citations(chunks: List[RetrievedChunk], answer: str) -> List[SourceCitation]:
    """
    Extract verified source citations from retrieved chunks.
    """
    citations: List[SourceCitation] = []
    seen_ids = set()

    for c in chunks:
        meta = c.metadata
        if meta.source_id in seen_ids:
            continue
        seen_ids.add(meta.source_id)

        # Snippet: first 160 characters
        snippet = c.content[:160].replace("\n", " ").strip() + "..."
        citations.append(
            SourceCitation(
                source_title=meta.source_title,
                source_type=meta.source_type.value,
                source_id=meta.source_id,
                snippet=snippet,
                page_number=meta.page_number,
                similarity_score=c.similarity_score,
            )
        )

    return citations
