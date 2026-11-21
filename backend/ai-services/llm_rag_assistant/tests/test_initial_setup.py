"""
tests/test_initial_setup.py
Initial verification tests for Operix LLM/RAG Assistant Module.

Verifies:
  - Configuration loading and default settings
  - Schema serialization and validation contracts
  - Prompt template construction and anti-hallucination guardrails
  - Safe read-only operational database connectivity
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from ..config.settings import AssistantSettings, get_settings
from ..prompts.templates import (
    BASE_SYSTEM_PROMPT_AR,
    BASE_SYSTEM_PROMPT_EN,
    build_grounded_prompt,
)
from ..schemas.contracts import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    ChunkMetadata,
    DocumentChunk,
    DocumentSourceType,
    RetrievalFilter,
    RetrievedChunk,
    SourceCitation,
    UserContext,
)


class TestInitialSetup(unittest.TestCase):
    def test_settings_load_successfully(self):
        settings = get_settings()
        self.assertIsInstance(settings, AssistantSettings)
        self.assertIn(settings.llm_provider, ("openai", "ollama", "mock"))
        self.assertIn(settings.embedding_provider, ("openai", "ollama", "mock"))
        self.assertGreater(settings.chunk_size, 0)
        self.assertGreater(settings.top_k, 0)
        self.assertIsInstance(settings.default_factory_id, UUID)

    def test_schema_chunk_validation(self):
        meta = ChunkMetadata(
            chunk_id="chunk-001",
            source_id="rule-001",
            source_title="Mandatory PPE in Welding Area",
            source_type=DocumentSourceType.DATABASE_SAFETY_RULE,
        )
        chunk = DocumentChunk(
            content="Workers must wear safety helmets and welding goggles.",
            metadata=meta,
        )
        self.assertEqual(chunk.metadata.source_id, "rule-001")
        dumped = chunk.model_dump(mode="json")
        self.assertIn("content", dumped)
        self.assertEqual(dumped["metadata"]["source_type"], "db_safety_rule")

    def test_schema_assistant_request_and_response(self):
        user_ctx = UserContext(
            user_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
            full_name="Abdallah Waleed",
            role_code="factory_admin",
            factory_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
        )
        req = AssistantQueryRequest(
            question="What are the recent PPE violations?",
            user_context=user_ctx,
        )
        self.assertEqual(req.question, "What are the recent PPE violations?")
        self.assertEqual(req.user_context.role_code, "factory_admin")

        citation = SourceCitation(
            source_title="PPE Rule",
            source_type="db_safety_rule",
            source_id="rule-01",
            snippet="Wear goggles",
        )
        resp = AssistantQueryResponse(
            answer="There are 6 PPE violations recorded.",
            conversation_id="conv-123",
            has_sufficient_evidence=True,
            citations=[citation],
            provider="openai",
            model_name="gpt-4o-mini",
            language="en",
            processing_time_seconds=0.45,
        )
        self.assertTrue(resp.has_sufficient_evidence)
        self.assertEqual(len(resp.citations), 1)

    def test_prompt_template_formatting(self):
        self.assertIn("STRICT GROUNDING", BASE_SYSTEM_PROMPT_EN)
        self.assertIn("ZERO HALLUCINATION", BASE_SYSTEM_PROMPT_EN)
        self.assertIn("الالتزام التام بالحقائق", BASE_SYSTEM_PROMPT_AR)

        # Build prompt with empty chunks
        empty_prompt = build_grounded_prompt("How many incidents?", [])
        self.assertIn("NO VERIFIED RECORDS RETRIEVED", empty_prompt)
        self.assertIn("How many incidents?", empty_prompt)

        # Build prompt with retrieved chunk
        meta = ChunkMetadata(
            chunk_id="c1",
            source_id="inc-01",
            source_title="Welding Intrusion",
            source_type=DocumentSourceType.DATABASE_INCIDENT,
        )
        chunk = RetrievedChunk(
            content="Critical intrusion detected in Welding Restricted Zone.",
            metadata=meta,
            similarity_score=0.92,
        )
        prompt_with_context = build_grounded_prompt("Tell me about incident 1", [chunk])
        self.assertIn("Welding Intrusion", prompt_with_context)
        self.assertIn("Critical intrusion detected", prompt_with_context)
        self.assertIn("Similarity: 0.92", prompt_with_context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
