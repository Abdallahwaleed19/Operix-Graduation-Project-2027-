"""
retrieval/vector_store.py
Isolated local vector store adapter and NumPy-accelerated implementation.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import numpy as np

from ..config.settings import get_settings
from ..schemas.contracts import DocumentChunk, RetrievalFilter, RetrievedChunk


class VectorStoreBase(ABC):
    """Abstract interface for vector index and metadata storage."""

    @abstractmethod
    def add_chunks(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> None:
        """Add chunks and corresponding embeddings to the store."""
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, search_filter: RetrievalFilter) -> List[RetrievedChunk]:
        """Search for top-K matching chunks matching the search filter."""
        pass

    @abstractmethod
    def save(self, directory: Optional[Path | str] = None) -> None:
        """Persist index and metadata to disk."""
        pass

    @abstractmethod
    def load(self, directory: Optional[Path | str] = None) -> bool:
        """Load index and metadata from disk."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Number of indexed chunks."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored vectors and documents."""
        pass


class NumPyVectorStore(VectorStoreBase):
    """
    Pure NumPy persistent vector index with cosine similarity search.
    Requires zero external C++ build tools, perfectly compatible with Windows.
    """

    def __init__(self, storage_dir: Optional[Path | str] = None) -> None:
        self.storage_dir = Path(storage_dir or get_settings().vector_store_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._chunks: List[DocumentChunk] = []
        self._embeddings: Optional[np.ndarray] = None

        # Automatically load index if files exist
        self.load(self.storage_dir)

    def count(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks = []
        self._embeddings = None

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: np.ndarray) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) does not match embeddings ({len(embeddings)})")

        if not chunks:
            return

        # Ensure embeddings are float32 and normalized
        arr = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norm_arr = arr / np.where(norms == 0, 1, norms)

        if self._embeddings is None or len(self._chunks) == 0:
            self._embeddings = norm_arr
            self._chunks = list(chunks)
        else:
            self._embeddings = np.vstack([self._embeddings, norm_arr])
            self._chunks.extend(chunks)

    def search(self, query_vector: np.ndarray, search_filter: RetrievalFilter) -> List[RetrievedChunk]:
        if self._embeddings is None or len(self._chunks) == 0:
            return []

        # Normalize query vector
        q = np.asarray(query_vector, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        # Compute cosine similarity across all stored vectors via dot product
        similarities = np.dot(self._embeddings, q)

        # Apply metadata filters and collect candidate indices
        results: List[RetrievedChunk] = []
        # Sort indices descending by similarity
        ranked_indices = np.argsort(-similarities)

        for idx in ranked_indices:
            score = float(similarities[idx])
            if score < search_filter.min_similarity:
                break  # Since array is sorted, remaining items will also be below threshold

            chunk = self._chunks[idx]
            meta = chunk.metadata

            # 1. Factory scoping (tenant isolation)
            if search_filter.factory_id and meta.factory_id:
                if str(meta.factory_id) != str(search_filter.factory_id):
                    continue

            # 2. Department scoping
            if search_filter.department_id and meta.department_id:
                if str(meta.department_id) != str(search_filter.department_id):
                    continue

            # 3. Source type filtering
            if search_filter.source_types:
                if meta.source_type not in search_filter.source_types:
                    continue

            results.append(
                RetrievedChunk(
                    content=chunk.content,
                    metadata=meta,
                    similarity_score=round(score, 4),
                )
            )

            if len(results) >= search_filter.top_k:
                break

        return results

    def save(self, directory: Optional[Path | str] = None) -> None:
        target_dir = Path(directory or self.storage_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Save embeddings array
        if self._embeddings is not None and len(self._embeddings) > 0:
            np.savez_compressed(target_dir / "index.npz", embeddings=self._embeddings)

        # Save metadata and chunks
        metadata_file = target_dir / "chunks.json"
        raw_chunks = [c.model_dump(mode="json") for c in self._chunks]
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(raw_chunks, f, ensure_ascii=False, indent=2)

    def load(self, directory: Optional[Path | str] = None) -> bool:
        target_dir = Path(directory or self.storage_dir)
        index_file = target_dir / "index.npz"
        metadata_file = target_dir / "chunks.json"

        if not index_file.exists() or not metadata_file.exists():
            return False

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                raw_chunks = json.load(f)
            loaded_chunks = [DocumentChunk.model_validate(c) for c in raw_chunks]

            with np.load(index_file) as data:
                loaded_embeddings = data["embeddings"]

            if len(loaded_chunks) == len(loaded_embeddings):
                self._chunks = loaded_chunks
                self._embeddings = loaded_embeddings
                return True
        except Exception as exc:
            print(f"[NumPyVectorStore] Could not load saved index: {exc}")
        return False
