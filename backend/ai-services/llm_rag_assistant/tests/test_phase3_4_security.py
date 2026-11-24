"""
llm_rag_assistant/tests/test_phase3_4_security.py
Adversarial tests for Phase 3 (Conversation Ownership & Tenant Isolation)
and Phase 4 (Action Validation & Centralized Delegation).
"""
from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from llm_rag_assistant.config import settings as assistant_settings
from llm_rag_assistant.llm.context_manager import ConversationManager, ConversationOwnershipError
from llm_rag_assistant.providers.embedding_provider import MockEmbeddingProvider
from llm_rag_assistant.providers.llm_provider import MockLLMProvider
from llm_rag_assistant.retrieval.retriever import KnowledgeRetriever
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore
from llm_rag_assistant.schemas.contracts import ActionExecutionRequest, AssistantQueryRequest, UserContext
from llm_rag_assistant.services.action_service import OperixActionService
from llm_rag_assistant.services.assistant_service import OperixAssistantService


class TestConversationOwnershipPhase3(unittest.TestCase):
    def setUp(self):
        self.f1 = uuid4()
        self.f2 = uuid4()
        self.u1 = uuid4()
        self.u2 = uuid4()
        self.mgr = ConversationManager()

    def test_cross_user_same_factory_blocked(self):
        cid = self.mgr.get_or_create_id("shared_conv", factory_id=self.f1, user_id=self.u1)
        self.mgr.add_turn(cid, "hello", "hi", factory_id=self.f1, user_id=self.u1)

        with self.assertRaises(ConversationOwnershipError):
            self.mgr.get_or_create_id(cid, factory_id=self.f1, user_id=self.u2)
        with self.assertRaises(ConversationOwnershipError):
            self.mgr.get_history(cid, factory_id=self.f1, user_id=self.u2)
        with self.assertRaises(ConversationOwnershipError):
            self.mgr.add_turn(cid, "hijack", "nope", factory_id=self.f1, user_id=self.u2)
        with self.assertRaises(ConversationOwnershipError):
            self.mgr.clear(cid, factory_id=self.f1, user_id=self.u2)

    def test_cross_factory_same_user_blocked(self):
        cid = self.mgr.get_or_create_id("factory_conv", factory_id=self.f1, user_id=self.u1)
        self.mgr.add_turn(cid, "secret", "data", factory_id=self.f1, user_id=self.u1)

        with self.assertRaises(ConversationOwnershipError):
            self.mgr.get_history(cid, factory_id=self.f2, user_id=self.u1)
        with self.assertRaises(ConversationOwnershipError):
            self.mgr.clear(cid, factory_id=self.f2, user_id=self.u1)

    def test_unauthenticated_clear_blocked(self):
        cid = self.mgr.get_or_create_id("owned_conv", factory_id=self.f1, user_id=self.u1)
        with self.assertRaises(ConversationOwnershipError):
            self.mgr.clear(cid)

    def test_owner_can_read_and_clear(self):
        cid = self.mgr.get_or_create_id("owner_conv", factory_id=self.f1, user_id=self.u1)
        self.mgr.add_turn(cid, "q1", "a1", factory_id=self.f1, user_id=self.u1)
        self.assertEqual(len(self.mgr.get_history(cid, factory_id=self.f1, user_id=self.u1)), 2)
        self.assertTrue(self.mgr.clear(cid, factory_id=self.f1, user_id=self.u1))
        self.assertEqual(len(self.mgr.get_history(cid, factory_id=self.f1, user_id=self.u1)), 0)

    def test_ask_requires_user_context(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            store = NumPyVectorStore(storage_dir=Path(tmp))
            retriever = KnowledgeRetriever(vector_store=store, embedding_provider=MockEmbeddingProvider())
            svc = OperixAssistantService(
                retriever=retriever,
                llm_provider=MockLLMProvider(),
                conversation_manager=self.mgr,
            )
            with self.assertRaises(ValueError):
                svc.ask(AssistantQueryRequest(question="What is PPE?"))

    def test_no_hardcoded_db_credentials_in_settings(self):
        text = Path(assistant_settings.__file__).read_text(encoding="utf-8")
        self.assertNotIn("postgresql+", text.lower())
        self.assertNotIn("operix_db", text.lower())


class TestActionIntegrationPhase4(unittest.TestCase):
    def setUp(self):
        self.svc = OperixActionService()
        self.f1 = uuid4()
        self.u1 = uuid4()

    def test_unsupported_action_rejected(self):
        req = ActionExecutionRequest(
            action_id="act-bad",
            action_type="drop_database",
            parameters={},
        )
        with self.assertRaises(ValueError):
            self.svc.execute(req)

    def test_missing_required_parameters_rejected(self):
        req = ActionExecutionRequest(
            action_id="act-no-inc",
            action_type="acknowledge_incident",
            parameters={},
        )
        with self.assertRaises(ValueError):
            self.svc.validate_request(req, authenticated_role="safety_supervisor")

    def test_operator_privileged_action_rejected(self):
        req = ActionExecutionRequest(
            action_id="act-priv",
            action_type="create_incident",
            parameters={},
            user_role="operator",
        )
        with self.assertRaises(PermissionError):
            self.svc.validate_request(req, authenticated_role="operator")

    def test_delegation_preserves_authenticated_identity_and_session(self):
        req = ActionExecutionRequest(
            action_id="act-ok",
            action_type="acknowledge_incident",
            parameters={"incident_id": str(uuid4())},
            factory_id=uuid4(),  # Untrusted payload factory_id must be ignored
            user_id=uuid4(),     # Untrusted payload user_id must be ignored
        )
        captured = {}

        class _FakeBackendActionService:
            async def execute_action(self, **kwargs):
                captured.update(kwargs)
                return {"status": "executed", "audit_reference": "AUDIT-1"}

        mock_db = MagicMock()
        coro = self.svc.execute_with_backend(
            backend_action_service=_FakeBackendActionService(),
            db=mock_db,
            factory_id=self.f1,
            user_id=self.u1,
            user_role="safety_supervisor",
            request=req,
        )
        try:
            coro.send(None)
            self.fail("Expected StopIteration")
        except StopIteration as stop:
            res = stop.value

        self.assertEqual(res["status"], "executed")
        self.assertEqual(captured["factory_id"], self.f1)
        self.assertEqual(captured["user_id"], self.u1)
        mock_db.commit.assert_not_called()
        mock_db.rollback.assert_not_called()
        mock_db.close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
