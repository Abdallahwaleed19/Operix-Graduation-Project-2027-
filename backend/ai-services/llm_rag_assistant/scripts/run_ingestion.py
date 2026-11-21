"""
scripts/run_ingestion.py
CLI script to execute knowledge ingestion from PostgreSQL and local documents,
compute embeddings, and persist the vector store index.

Usage:
    python -m llm_rag_assistant.scripts.run_ingestion
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add backend/ai-services to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from llm_rag_assistant.config.settings import get_settings
from llm_rag_assistant.ingestion.pipeline import KnowledgeIngestionPipeline
from llm_rag_assistant.providers.embedding_provider import get_embedding_provider
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore


def main() -> int:
    print("=" * 70)
    print("  Operix — Knowledge Ingestion & Vector Indexing Runner")
    print("=" * 70)

    settings = get_settings()
    docs_dir = Path(__file__).resolve().parent.parent / "data" / "documents"

    print(f"\n[1] Starting Knowledge Ingestion Pipeline...")
    print(f"    - Chunk Size          : {settings.chunk_size}")
    print(f"    - Chunk Overlap       : {settings.chunk_overlap}")
    print(f"    - Documents Path      : {docs_dir}")
    print(f"    - Database URL        : {settings.database_url.split('@')[-1]}")

    pipeline = KnowledgeIngestionPipeline()
    t0 = time.perf_counter()
    chunks, summary = pipeline.run(
        factory_id=settings.default_factory_id,
        documents_dir=docs_dir,
        include_database=True,
    )
    ingest_time = time.perf_counter() - t0

    print(f"\n[2] Ingestion Complete in {ingest_time:.2f}s:")
    print(f"    - Documents Scanned   : {summary.total_documents_scanned}")
    print(f"    - Chunks Created      : {summary.total_chunks_created}")
    print(f"    - Duplicates Skipped  : {summary.skipped_documents}")
    for src in summary.sources_ingested:
        print(f"      • {src}")

    if not chunks:
        print("[!] No chunks were produced. Vector index update skipped.")
        return 0

    print(f"\n[3] Generating Embeddings...")
    print(f"    - Embedding Provider  : {settings.embedding_provider}")
    provider = get_embedding_provider()
    print(f"    - Model Name          : {provider.model_name}")
    print(f"    - Dimension           : {provider.dimension}")

    t1 = time.perf_counter()
    texts = [c.content for c in chunks]
    embeddings = provider.embed_texts(texts)
    embed_time = time.perf_counter() - t1
    print(f"    - Embeddings Generated: {len(embeddings)} vectors in {embed_time:.2f}s")

    print(f"\n[4] Persisting to Vector Store...")
    vector_store = NumPyVectorStore(storage_dir=settings.vector_store_dir)
    vector_store.clear()
    vector_store.add_chunks(chunks, embeddings)
    vector_store.save()

    print(f"    - Target Directory    : {settings.vector_store_dir}")
    print(f"    - Indexed Chunks      : {vector_store.count()}")
    print("\n[SUCCESS] Knowledge ingestion & vector indexing completed successfully!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
