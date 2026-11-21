"""
retrieval/retriever.py
High-level semantic knowledge retrieval engine for Operix Assistant.
"""
from __future__ import annotations

import time
from typing import Optional

from ..config.settings import get_settings
from ..providers.embedding_provider import EmbeddingProviderBase, get_embedding_provider
from ..schemas.contracts import RetrievalFilter, RetrievalResult
from .vector_store import NumPyVectorStore, VectorStoreBase


class KnowledgeRetriever:
    """Semantic retrieval coordinator marrying embedding generation with vector search."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProviderBase] = None,
        vector_store: Optional[VectorStoreBase] = None,
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or NumPyVectorStore()

    def retrieve(
        self,
        query: str,
        search_filter: Optional[RetrievalFilter] = None,
    ) -> RetrievalResult:
        """
        Embed query, execute filtered similarity search, and construct RetrievalResult.
        """
        start_time = time.perf_counter()
        settings = get_settings()

        effective_filter = search_filter or RetrievalFilter(
            top_k=settings.top_k,
            min_similarity=settings.similarity_threshold,
        )

        if not query or not query.strip():
            return RetrievalResult(
                query=query,
                chunks=[],
                has_sufficient_evidence=False,
                retrieval_latency_ms=0.0,
            )

        # 1. Embed query vector
        query_vector = self.embedding_provider.embed_query(query)

        # 2. Vector search in local index
        chunks = self.vector_store.search(query_vector, effective_filter)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Sufficient evidence exists if at least one chunk was retrieved above threshold
        has_evidence = len(chunks) > 0 and chunks[0].similarity_score >= effective_filter.min_similarity

        return RetrievalResult(
            query=query,
            chunks=chunks,
            has_sufficient_evidence=has_evidence,
            retrieval_latency_ms=round(latency_ms, 2),
        )
