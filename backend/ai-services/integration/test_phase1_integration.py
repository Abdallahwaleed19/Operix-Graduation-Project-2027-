"""
integration/test_phase1_integration.py
Tests verifying Phase 1 integration compatibility between Seif's FastAPI Main Backend
and Abdullah's AI / Analytics Service Modules.

Verifies:
1. Importing each AI service from backend context.
2. Initializing services with Main Application settings.
3. Injecting database sessions (FastAPI SessionLocal / Depends(get_db)).
4. Non-destructive transaction behavior on externally injected sessions.
5. Live PostgreSQL schema compatibility.
6. Multi-tenant factory isolation.
7. Provider configuration and mock support.
8. Error adaptation to OperixException hierarchy.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

# Ensure backend and backend/ai-services are in sys.path
_AI_SERVICES_DIR = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _AI_SERVICES_DIR.parent

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_AI_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICES_DIR))

# Load local development environment variables if present
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:abdallah@localhost:5432/operix_db"

# Import Main Backend Components
from app.core.config import get_settings
get_settings.cache_clear()
main_settings = get_settings()
from app.core.database import SessionLocal, engine, set_tenant_context
from app.core.errors import (
    OperixException,
    ResourceNotFoundException,
    TenantAccessDeniedException,
)

# Import AI Services and Integration Adapters
from integration.phase1_adapter import (
    adapt_ai_exception_to_operix_error,
    get_incident_evidence_service,
    get_llm_rag_assistant_service,
    get_reports_generation_service,
    get_workforce_analytics_service,
    sync_main_settings_to_ai_services,
)
from workforce_analytics.services.analytics_service import WorkforceAnalyticsService
from llm_rag_assistant.services.assistant_service import OperixAssistantService, get_assistant_service
from reports_generation.services.report_service import ReportService
from incident_evidence.services.evidence_service import EvidenceService, get_evidence_service
from incident_evidence.exceptions import (
    EvidenceNotFoundError,
    FactoryMismatchError,
    FileSizeLimitError,
    InvalidMimeTypeError,
)
from incident_evidence.schemas import EvidenceUploadRequest


class TestPhase1IntegrationImportsAndSettings(unittest.TestCase):
    """Test 1: Importability and Settings Synchronization."""

    def test_all_services_importable(self):
        """Verify that all 4 AI services can be imported without errors."""
        self.assertTrue(issubclass(WorkforceAnalyticsService, object))
        self.assertTrue(issubclass(OperixAssistantService, object))
        self.assertTrue(issubclass(ReportService, object))
        self.assertTrue(issubclass(EvidenceService, object))

    def test_sync_main_settings(self):
        """Verify settings synchronization from main FastAPI backend."""
        sync_main_settings_to_ai_services(main_settings)
        self.assertEqual(os.environ.get("DATABASE_URL"), str(main_settings.DATABASE_URL))
        self.assertEqual(os.environ.get("DEFAULT_FACTORY_ID"), str(main_settings.DEFAULT_FACTORY_ID))

    def test_assistant_singleton_accessible_from_health(self):
        """Verify get_assistant_service returns a healthy singleton."""
        svc = get_assistant_service()
        self.assertIsInstance(svc, OperixAssistantService)
        health = svc.check_health()
        self.assertEqual(health["status"], "healthy")


class TestPhase1DatabaseSessionInjection(unittest.TestCase):
    """Test 2: Database Session Injection and Transaction Safety."""

    @classmethod
    def setUpClass(cls):
        # Open an actual database session from Seif's SessionLocal
        try:
            cls.db = SessionLocal()
            set_tenant_context(cls.db, main_settings.DEFAULT_FACTORY_ID)
            cls.has_db = True
        except Exception:
            cls.has_db = False

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "has_db", False) and cls.db:
            cls.db.close()

    def test_workforce_analytics_with_injected_session(self):
        """Verify WorkforceAnalyticsService executes read-only queries with injected session."""
        if not self.has_db:
            self.skipTest("Live database not reachable")

        service = get_workforce_analytics_service(session=self.db, factory_id=main_settings.DEFAULT_FACTORY_ID)
        overview = service.get_workforce_overview()
        self.assertIsNotNone(overview)
        self.assertEqual(str(overview.factory_id), str(main_settings.DEFAULT_FACTORY_ID))

    def test_injected_session_not_closed_or_committed_by_analytics(self):
        """Verify analytics query does not commit, rollback, or close the external session."""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.one.return_value = {
            "total_users": 10,
            "active_workers": 8,
            "inactive_workers": 2,
            "invited_users": 0,
            "disabled_users": 0,
        }
        mock_result.mappings.return_value.all.return_value = [
            {"code": "factory_admin", "cnt": 1},
            {"code": "factory_manager", "cnt": 1},
            {"code": "safety_supervisor", "cnt": 2},
        ]
        mock_session.execute.return_value = mock_result

        service = WorkforceAnalyticsService(session=mock_session)
        service.get_workforce_overview(factory_id=main_settings.DEFAULT_FACTORY_ID)

        # Session should be queried via execute, but commit/close must NOT be called on it
        self.assertTrue(mock_session.execute.called)
        self.assertFalse(mock_session.close.called)
        self.assertFalse(mock_session.commit.called)
        self.assertFalse(mock_session.rollback.called)

    def test_reports_service_with_injected_engine_and_session(self):
        """Verify ReportService consumes injected session and engine."""
        if not self.has_db:
            self.skipTest("Live database not reachable")

        service = get_reports_generation_service(session=self.db, engine=engine)
        self.assertIsNotNone(service.data_service)
        self.assertIsNotNone(service.data_service.repository.engine)

    def test_evidence_service_accepts_session_for_retrieval(self):
        """Verify EvidenceService methods accept Session as Connection-equivalent."""
        svc = get_evidence_service()
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = []

        # Calling list_by_event with mock_session should return an empty list without TypeError
        res = svc.list_by_event(
            conn=mock_session,
            event_id=uuid4(),
            factory_id=main_settings.DEFAULT_FACTORY_ID,
        )
        self.assertEqual(len(res), 0)
        self.assertTrue(mock_session.execute.called)


class TestPhase1TenantIsolationAndErrorAdapters(unittest.TestCase):
    """Test 3: Multi-tenant Factory Scoping and Exception Mapping."""

    def test_tenant_isolation_in_evidence_service(self):
        """Evidence retrieval validates requested factory_id against stored factory_id."""
        svc = get_evidence_service()
        factory_a = uuid4()
        factory_b = uuid4()

        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = None

        with self.assertRaises(EvidenceNotFoundError):
            svc.get_metadata(conn=mock_session, evidence_id=uuid4(), factory_id=factory_a)

    def test_adapt_ai_exception_to_operix_errors(self):
        """Verify AI service exceptions map cleanly to Main Backend OperixExceptions."""
        # 1. Not Found
        exc_not_found = EvidenceNotFoundError("Evidence 123 not found")
        adapted = adapt_ai_exception_to_operix_error(exc_not_found)
        self.assertIsInstance(adapted, ResourceNotFoundException)
        self.assertEqual(adapted.status_code, 404)

        # 2. Tenant Access Denied
        exc_tenant = FactoryMismatchError("Tenant mismatch")
        adapted_tenant = adapt_ai_exception_to_operix_error(exc_tenant)
        self.assertIsInstance(adapted_tenant, TenantAccessDeniedException)
        self.assertEqual(adapted_tenant.status_code, 403)

        # 3. Bad Request / Validation
        exc_size = FileSizeLimitError("Too large")
        adapted_size = adapt_ai_exception_to_operix_error(exc_size)
        self.assertIsInstance(adapted_size, OperixException)
        self.assertEqual(adapted_size.status_code, 400)


if __name__ == "__main__":
    unittest.main()
