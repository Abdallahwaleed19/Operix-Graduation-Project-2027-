"""
tests/test_end_to_end.py
End-to-end integration test verifying the full RAG cycle:
Ingestion -> Vector Indexing -> Storage -> Retrieval -> Assistant Generation -> Benchmark Evaluation.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from ..evaluation.evaluator import RAGEvaluator
from ..ingestion.pipeline import KnowledgeIngestionPipeline
from ..llm.context_manager import ConversationOwnershipError
from ..providers.embedding_provider import MockEmbeddingProvider
from ..providers.llm_provider import MockLLMProvider
from ..retrieval.retriever import KnowledgeRetriever
from ..retrieval.vector_store import NumPyVectorStore
from ..schemas.contracts import AssistantQueryRequest, UserContext
from ..services.assistant_service import OperixAssistantService


class TestEndToEndRAG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_factory_id = uuid4()
        cls.test_user_id = uuid4()
        cls.test_user_context = UserContext(
            user_id=cls.test_user_id,
            full_name="E2E Test Supervisor",
            role_code="safety_supervisor",
            factory_id=cls.test_factory_id,
        )
        cls.embedding_provider = MockEmbeddingProvider(dimension=384)
        cls.llm_provider = MockLLMProvider()
        cls.vector_store = NumPyVectorStore(storage_dir=cls.temp_dir)
        cls.retriever = KnowledgeRetriever(
            embedding_provider=cls.embedding_provider,
            vector_store=cls.vector_store,
        )

        # 1. Run Ingestion Pipeline
        doc_dir = Path(__file__).resolve().parent.parent / "data" / "documents"
        pipeline = KnowledgeIngestionPipeline(chunk_size=350, chunk_overlap=70)
        chunks, summary = pipeline.run(
            documents_dir=doc_dir,
            include_database=True,
        )
        cls.chunks = chunks
        cls.summary = summary

        # 2. Embed and Index chunks into Vector Store
        embeddings = cls.embedding_provider.embed_texts([c.content for c in chunks])
        cls.vector_store.add_chunks(chunks, embeddings)
        cls.vector_store.save()

        # 3. Instantiate Service
        cls.service = OperixAssistantService(
            retriever=cls.retriever,
            llm_provider=cls.llm_provider,
        )

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_e2e_ingestion_counts(self):
        self.assertGreater(self.summary.total_chunks_created, 10)
        self.assertEqual(self.vector_store.count(), len(self.chunks))

    def test_e2e_query_safety_rule(self):
        req = AssistantQueryRequest(
            question="What are the PPE violation rules in the welding area?",
            user_context=self.test_user_context,
        )
        resp = self.service.ask(req)
        self.assertTrue(resp.has_sufficient_evidence)
        self.assertGreater(len(resp.citations), 0)
        self.assertIn("Source:", resp.answer)

    def test_e2e_query_incident(self):
        req = AssistantQueryRequest(
            question="What happened in the restricted zone intrusion incident?",
            user_context=self.test_user_context,
        )
        resp = self.service.ask(req)
        self.assertTrue(resp.has_sufficient_evidence)
        self.assertGreater(len(resp.citations), 0)

    def test_e2e_unknown_query_honest_refusal(self):
        req = AssistantQueryRequest(
            question="What is the internal accounting budget for 2029?",
            user_context=self.test_user_context,
        )
        resp = self.service.ask(req)
        self.assertFalse(resp.has_sufficient_evidence)
        self.assertEqual(len(resp.citations), 0)

    def test_e2e_benchmark_evaluator(self):
        evaluator = RAGEvaluator(self.service, user_context=self.test_user_context)
        results = evaluator.evaluate()
        self.assertEqual(results["total_cases"], 8)
        self.assertGreaterEqual(results["grounding_accuracy_pct"], 75.0)
        self.assertEqual(results["refusal_honesty_pct"], 100.0)

    def test_e2e_evaluator_requires_explicit_user_context(self):
        evaluator = RAGEvaluator(self.service)
        with self.assertRaises(ValueError):
            evaluator.evaluate()

    def test_e2e_owner_can_access_own_conversation(self):
        req1 = AssistantQueryRequest(
            question="What are the PPE violation rules in the welding area?",
            user_context=self.test_user_context,
        )
        resp1 = self.service.ask(req1)
        req2 = AssistantQueryRequest(
            question="Summarize the safety rule.",
            conversation_id=resp1.conversation_id,
            user_context=self.test_user_context,
        )
        resp2 = self.service.ask(req2)
        self.assertEqual(resp2.conversation_id, resp1.conversation_id)

    def test_e2e_different_user_same_factory_blocked(self):
        req1 = AssistantQueryRequest(
            question="What are the PPE violation rules in the welding area?",
            user_context=self.test_user_context,
        )
        resp1 = self.service.ask(req1)
        other_user = UserContext(
            user_id=uuid4(),
            full_name="Other User",
            role_code="safety_supervisor",
            factory_id=self.test_factory_id,
        )
        req_hijack = AssistantQueryRequest(
            question="Continue previous conversation",
            conversation_id=resp1.conversation_id,
            user_context=other_user,
        )
        with self.assertRaises(ConversationOwnershipError):
            self.service.ask(req_hijack)

    def test_e2e_different_factory_blocked(self):
        req1 = AssistantQueryRequest(
            question="What are the PPE violation rules in the welding area?",
            user_context=self.test_user_context,
        )
        resp1 = self.service.ask(req1)
        other_factory_user = UserContext(
            user_id=self.test_user_id,
            full_name="Same User Other Factory",
            role_code="safety_supervisor",
            factory_id=uuid4(),
        )
        req_hijack = AssistantQueryRequest(
            question="Continue previous conversation",
            conversation_id=resp1.conversation_id,
            user_context=other_factory_user,
        )
        with self.assertRaises(ConversationOwnershipError):
            self.service.ask(req_hijack)

    def test_e2e_missing_user_context_rejected(self):
        req = AssistantQueryRequest(
            question="What are the PPE violation rules in the welding area?",
            user_context=None,
        )
        with self.assertRaises(ValueError):
            self.service.ask(req)


if __name__ == "__main__":
    unittest.main(verbosity=2)
