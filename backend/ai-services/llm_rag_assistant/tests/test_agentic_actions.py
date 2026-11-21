"""
tests/test_agentic_actions.py
Unit and integration tests for Agentic Remediation & Action Proposals.
"""
import unittest
from uuid import UUID

from llm_rag_assistant.llm.remediation_engine import RemediationEngine
from llm_rag_assistant.providers.embedding_provider import MockEmbeddingProvider
from llm_rag_assistant.providers.llm_provider import MockLLMProvider
from llm_rag_assistant.retrieval.retriever import KnowledgeRetriever
from llm_rag_assistant.retrieval.vector_store import NumPyVectorStore
from llm_rag_assistant.schemas.contracts import (
    ActionExecutionRequest,
    AssistantQueryRequest,
    UserContext,
)
from llm_rag_assistant.services.action_service import OperixActionService
from llm_rag_assistant.services.assistant_service import OperixAssistantService


class TestAgenticActions(unittest.TestCase):

    def setUp(self) -> None:
        self.vector_store = NumPyVectorStore()
        self.vector_store.load()
        self.retriever = KnowledgeRetriever(MockEmbeddingProvider(), self.vector_store)
        self.service = OperixAssistantService(
            retriever=self.retriever,
            llm_provider=MockLLMProvider(),
        )
        self.action_service = OperixActionService()
        self.user_ctx = UserContext(
            user_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
            full_name="Safety Lead",
            role_code="factory_admin",
            factory_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
        )

    def test_camera_maintenance_proposes_action(self) -> None:
        """Querying inactive cameras must generate maintenance and alert actions."""
        req = AssistantQueryRequest(
            question="Which cameras are currently inactive or undergoing maintenance?",
            user_context=self.user_ctx,
            language_preference="en",
        )
        resp = self.service.ask(req)

        self.assertTrue(resp.has_sufficient_evidence)
        self.assertGreater(len(resp.suggested_actions), 0)
        action_types = [a.action_type for a in resp.suggested_actions]
        self.assertIn("maintenance", action_types)
        self.assertIn("alert", action_types)

    def test_arabic_welding_ppe_proposes_arabic_actions(self) -> None:
        """Querying PPE safety in Arabic must generate localized Arabic actions."""
        req = AssistantQueryRequest(
            question="ما هي قواعد ومعدات الوقاية المعتمدة في منطقة اللحام؟",
            user_context=self.user_ctx,
            language_preference="ar",
        )
        resp = self.service.ask(req)

        self.assertTrue(resp.has_sufficient_evidence)
        self.assertGreater(len(resp.suggested_actions), 0)
        first_act = resp.suggested_actions[0]
        # Should have Arabic characters in title
        self.assertTrue(any("\u0600" <= c <= "\u06ff" for c in first_act.title))
        self.assertEqual(first_act.severity, "high")

    def test_out_of_scope_query_produces_zero_actions(self) -> None:
        """Non-evidence queries must NOT generate any suggested actions."""
        req = AssistantQueryRequest(
            question="What is the chemical formula of the cafeteria coffee?",
            user_context=self.user_ctx,
            language_preference="en",
        )
        resp = self.service.ask(req)

        self.assertFalse(resp.has_sufficient_evidence)
        self.assertEqual(len(resp.suggested_actions), 0)

    def test_action_execution_audit(self) -> None:
        """Executing an authorized action produces an audit record."""
        exec_req = ActionExecutionRequest(
            action_id="act-test-01",
            action_type="maintenance",
            parameters={"camera_name": "Maint-CAM-01", "department": "Maintenance"},
            confirmed_by="Supervisor_Abdallah",
        )
        res = self.action_service.execute(exec_req)

        self.assertEqual(res.status, "executed")
        self.assertTrue(res.audit_reference.startswith("AUDIT-"))
        self.assertIn("Maint-CAM-01", res.message)

        # Verify audit history
        audit = self.action_service.get_audit_trail()
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["confirmed_by"], "Supervisor_Abdallah")


if __name__ == "__main__":
    unittest.main()
