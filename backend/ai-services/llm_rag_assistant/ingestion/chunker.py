"""
ingestion/chunker.py
Sentence-aware and section-aware document chunking.

Ensures safety regulations and operational sentences are not severed across
half-sentences, preserving full contextual meaning.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional
from uuid import UUID

from ..schemas.contracts import DocumentChunk, DocumentSourceType
from .metadata import create_metadata
from .text_processor import clean_text


class DocumentChunker:
    """Configurable sentence-boundary-preserving document chunker."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences supporting English and Arabic punctuation (. ? ! ؟ \n\n).
        """
        # Split on sentence terminals while keeping structural breaks
        pattern = r"(?<=[.!?؟\n])\s+"
        raw_parts = re.split(pattern, text)
        sentences = [p.strip() for p in raw_parts if p.strip()]
        return sentences

    def chunk_text(
        self,
        text: str,
        source_id: str,
        source_title: str,
        source_type: DocumentSourceType,
        factory_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        page_number: Optional[int] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """
        Break text into overlapping chunks honoring sentence boundaries.
        """
        cleaned = clean_text(text)
        if not cleaned:
            return []

        # If document is already smaller than chunk size, return single chunk
        if len(cleaned) <= self.chunk_size:
            meta = create_metadata(
                source_id=source_id,
                source_title=source_title,
                source_type=source_type,
                content=cleaned,
                factory_id=factory_id,
                department_id=department_id,
                page_number=page_number,
                extra=extra,
            )
            return [DocumentChunk(content=cleaned, metadata=meta, token_estimate=max(1, len(cleaned) // 4))]

        sentences = self._split_into_sentences(cleaned)
        chunks: List[DocumentChunk] = []

        current_sentences: List[str] = []
        current_len = 0

        for s in sentences:
            s_len = len(s)

            # If a single sentence exceeds chunk_size, hard-split it
            if s_len > self.chunk_size:
                # Flush existing buffer
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    meta = create_metadata(
                        source_id=source_id,
                        source_title=source_title,
                        source_type=source_type,
                        content=chunk_text,
                        factory_id=factory_id,
                        department_id=department_id,
                        page_number=page_number,
                        extra=extra,
                    )
                    chunks.append(DocumentChunk(content=chunk_text, metadata=meta, token_estimate=len(chunk_text) // 4))
                    current_sentences = []
                    current_len = 0

                # Slice large sentence
                start = 0
                while start < s_len:
                    sub = s[start : start + self.chunk_size]
                    meta = create_metadata(
                        source_id=source_id,
                        source_title=source_title,
                        source_type=source_type,
                        content=sub,
                        factory_id=factory_id,
                        department_id=department_id,
                        page_number=page_number,
                        extra=extra,
                    )
                    chunks.append(DocumentChunk(content=sub, metadata=meta, token_estimate=len(sub) // 4))
                    start += self.chunk_size - self.chunk_overlap
                continue

            if current_len + s_len + 1 <= self.chunk_size:
                current_sentences.append(s)
                current_len += s_len + 1
            else:
                # Flush current chunk
                chunk_text = " ".join(current_sentences)
                meta = create_metadata(
                    source_id=source_id,
                    source_title=source_title,
                    source_type=source_type,
                    content=chunk_text,
                    factory_id=factory_id,
                    department_id=department_id,
                    page_number=page_number,
                    extra=extra,
                )
                chunks.append(DocumentChunk(content=chunk_text, metadata=meta, token_estimate=len(chunk_text) // 4))

                # Retain overlap sentences
                overlap_sentences: List[str] = []
                overlap_len = 0
                for rev_s in reversed(current_sentences):
                    if overlap_len + len(rev_s) + 1 <= self.chunk_overlap:
                        overlap_sentences.insert(0, rev_s)
                        overlap_len += len(rev_s) + 1
                    else:
                        break

                current_sentences = overlap_sentences + [s]
                current_len = sum(len(x) + 1 for x in current_sentences)

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            meta = create_metadata(
                source_id=source_id,
                source_title=source_title,
                source_type=source_type,
                content=chunk_text,
                factory_id=factory_id,
                department_id=department_id,
                page_number=page_number,
                extra=extra,
            )
            chunks.append(DocumentChunk(content=chunk_text, metadata=meta, token_estimate=len(chunk_text) // 4))

        return chunks
