"""
ingestion/pipeline.py
End-to-end ingestion pipeline orchestrator.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from ..config.settings import get_settings
from ..schemas.contracts import DocumentChunk, IngestionSummary
from .chunker import DocumentChunker
from .database_loader import DatabaseKnowledgeLoader
from .document_loader import DocumentLoader, RawDocument


class KnowledgeIngestionPipeline:
    """Orchestrates document discovery, database extraction, normalization, and chunking."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        database_url: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size or settings.chunk_size,
            chunk_overlap=chunk_overlap or settings.chunk_overlap,
        )
        self.db_loader = DatabaseKnowledgeLoader(database_url or settings.database_url)
        self.doc_loader = DocumentLoader()

    def run(
        self,
        factory_id: Optional[UUID] = None,
        documents_dir: Optional[Path | str] = None,
        include_database: bool = True,
    ) -> tuple[List[DocumentChunk], IngestionSummary]:
        """
        Execute full ingestion cycle. Deduplicates chunks by chunk_id.
        """
        start_time = time.perf_counter()
        raw_documents: List[RawDocument] = []
        sources_list: List[str] = []

        # 1. Ingest from database
        if include_database:
            try:
                db_docs = self.db_loader.extract_all(factory_id)
                raw_documents.extend(db_docs)
                sources_list.append(f"PostgreSQL ({len(db_docs)} records)")
            except Exception as exc:
                print(f"[KnowledgeIngestionPipeline] DB extraction warning: {exc}")

        # 2. Ingest from files (PDF/MD/TXT)
        if documents_dir:
            path = Path(documents_dir)
            if path.exists():
                file_docs = self.doc_loader.load_directory(path, factory_id=factory_id)
                raw_documents.extend(file_docs)
                sources_list.append(f"Directory {path.name} ({len(file_docs)} files)")

        # 3. Chunk and Deduplicate
        seen_chunk_ids: set[str] = set()
        final_chunks: List[DocumentChunk] = []
        skipped_duplicates = 0

        for doc in raw_documents:
            chunks = self.chunker.chunk_text(
                text=doc.content,
                source_id=doc.source_id,
                source_title=doc.source_title,
                source_type=doc.source_type,
                page_number=doc.page_number,
                factory_id=doc.factory_id,
                department_id=doc.department_id,
            )
            for chk in chunks:
                if chk.metadata.chunk_id in seen_chunk_ids:
                    skipped_duplicates += 1
                    continue
                seen_chunk_ids.add(chk.metadata.chunk_id)
                final_chunks.append(chk)

        duration = time.perf_counter() - start_time
        summary = IngestionSummary(
            total_documents_scanned=len(raw_documents),
            total_chunks_created=len(final_chunks),
            sources_ingested=sources_list,
            skipped_documents=skipped_duplicates,
            duration_seconds=round(duration, 3),
            status="completed",
        )

        return final_chunks, summary
