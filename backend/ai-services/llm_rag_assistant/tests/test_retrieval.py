"""
tests/test_retrieval.py
Unit and integration tests for Embeddings, Vector Storage, and Knowledge Retrieval.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID

import numpy as np

from ..providers.embedding_provider import MockEmbeddingProvider
from ..retrieval.retriever import KnowledgeRetriever
from ..retrieval.vector_store import NumPyVectorStore
from ..schemas.contracts import (
    ChunkMetadata,
    DocumentChunk,
    DocumentSourceType,
    RetrievalFilter,
)


class TestEmbeddingProvider(unittest.TestCase):
    def setUp(self):
        self.provider = MockEmbeddingProvider(dimension=64)

    def test_embedding_dimensions(self):
        vec = self.provider.embed_query("PPE Violation in Welding")
        self.assertEqual(vec.shape, (64,))
        # Unit normalized vector
        self.assertAlmostEqual(np.linalg.norm(vec), 1.0, places=4)

    def test_deterministic_embedding(self):
        v1 = self.provider.embed_query("Safety Rule")
        v2 = self.provider.embed_query("Safety Rule")
        np.testing.assert_array_almost_equal(v1, v2)

    def test_batch_embeddings(self):
        batch = ["Text one", "Text two", "Text three"]
        mat = self.provider.embed_texts(batch)
        self.assertEqual(mat.shape, (3, 64))


class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = NumPyVectorStore(storage_dir=self.temp_dir)
        self.provider = MockEmbeddingProvider(dimension=32)

        # Seed 3 sample chunks
        self.f1 = UUID("aaaaaaaa-0001-0001-0001-000000000001")
        self.f2 = UUID("bbbbbbbb-0002-0002-0002-000000000002")

        c1 = DocumentChunk(
            content="Goggles are mandatory in the welding area.",
            metadata=ChunkMetadata(
                chunk_id="c1",
                source_id="rule-1",
                source_title="PPE Rule",
                source_type=DocumentSourceType.DATABASE_SAFETY_RULE,
                factory_id=self.f1,
            ),
        )
        c2 = DocumentChunk(
            content="Incident #123: unauthorized worker entered robotic cell.",
            metadata=ChunkMetadata(
                chunk_id="c2",
                source_id="inc-123",
                source_title="Intrusion Incident",
                source_type=DocumentSourceType.DATABASE_INCIDENT,
                factory_id=self.f1,
            ),
        )
        c3 = DocumentChunk(
            content="Chemical storage guidelines for Factory B.",
            metadata=ChunkMetadata(
                chunk_id="c3",
                source_id="doc-chem",
                source_title="Chemical Policy",
                source_type=DocumentSourceType.MANUAL_TEXT,
                factory_id=self.f2,
            ),
        )
        self.chunks = [c1, c2, c3]
        embeddings = self.provider.embed_texts([c.content for c in self.chunks])
        self.store.add_chunks(self.chunks, embeddings)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_count(self):
        self.assertEqual(self.store.count(), 3)

    def test_search_and_similarity(self):
        q_vec = self.provider.embed_query("welding area goggles")
        flt = RetrievalFilter(top_k=2, min_similarity=0.0)
        results = self.store.search(q_vec, flt)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 2)
        # Scores should be sorted descending
        if len(results) > 1:
            self.assertGreaterEqual(results[0].similarity_score, results[1].similarity_score)

    def test_tenant_factory_isolation(self):
        q_vec = self.provider.embed_query("storage guidelines")
        # Filter for Factory 1 only -> should never return chunk c3 belonging to Factory 2
        flt = RetrievalFilter(factory_id=self.f1, top_k=5, min_similarity=0.0)
        results = self.store.search(q_vec, flt)
        for r in results:
            self.assertEqual(r.metadata.factory_id, self.f1)
            self.assertNotEqual(r.metadata.source_id, "doc-chem")

    def test_source_type_filtering(self):
        q_vec = self.provider.embed_query("incident details")
        flt = RetrievalFilter(
            source_types=[DocumentSourceType.DATABASE_INCIDENT],
            top_k=5,
            min_similarity=0.0,
        )
        results = self.store.search(q_vec, flt)
        for r in results:
            self.assertEqual(r.metadata.source_type, DocumentSourceType.DATABASE_INCIDENT)

    def test_save_and_load_persistence(self):
        self.store.save()
        # Create a new store instance pointing to the same folder
        new_store = NumPyVectorStore(storage_dir=self.temp_dir)
        self.assertEqual(new_store.count(), 3)


class TestKnowledgeRetriever(unittest.TestCase):
    def setUp(self):
        self.provider = MockEmbeddingProvider(dimension=32)
        self.store = NumPyVectorStore(storage_dir=tempfile.mkdtemp())
        self.retriever = KnowledgeRetriever(embedding_provider=self.provider, vector_store=self.store)

        c1 = DocumentChunk(
            content="Hard hats must be worn at all construction sites.",
            metadata=ChunkMetadata(
                chunk_id="c1",
                source_id="rule-hat",
                source_title="Hard Hat Rule",
                source_type=DocumentSourceType.DATABASE_SAFETY_RULE,
            ),
        )
        self.store.add_chunks([c1], self.provider.embed_texts([c1.content]))

    def test_retrieve_query_success(self):
        res = self.retriever.retrieve("hard hat rule", RetrievalFilter(top_k=1, min_similarity=0.0))
        self.assertEqual(len(res.chunks), 1)
        self.assertTrue(res.has_sufficient_evidence)
        self.assertGreaterEqual(res.retrieval_latency_ms, 0.0)

    def test_retrieve_empty_query(self):
        res = self.retriever.retrieve("", RetrievalFilter(top_k=5))
        self.assertEqual(len(res.chunks), 0)
        self.assertFalse(res.has_sufficient_evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
