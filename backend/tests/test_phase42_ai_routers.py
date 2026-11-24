"""
tests/test_phase42_ai_routers.py
Phase 4.2 — FastAPI AI Services Routers Tests.
Covers:
  - Analytics router endpoints (overview, attendance, incidents, productivity, camera-coverage, summary)
  - Assistant router endpoints (ask, sources, conversations, health)
  - Reports router endpoints (generate, list, get, download, path traversal protection)
  - Evidence router endpoints (upload, list, get, download, verify-integrity)
  - Strict tenant boundary verification on all routers
"""
from __future__ import annotations

import base64
from datetime import date, datetime, timezone
import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.ai_deps import (
    get_evidence_service_dep,
    get_llm_assistant_service_dep,
    get_reports_service_dep,
    get_workforce_analytics_service_dep,
)
from app.api.deps import AuthenticatedUser, get_current_factory_id, get_current_user_context, get_tenant_db
from app.core.config import settings
from app.core.database import SessionLocal
from app.main import create_application
from app.schemas.common import APIResponse

FACTORY_1 = UUID("aaaaaaaa-0001-0001-0001-000000000001")
FACTORY_2 = UUID("bbbbbbbb-0002-0002-0002-000000000002")


@pytest.fixture
def test_app():
    return create_application()


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


# ---------------------------------------------------------------------------
# 1. Workforce Analytics Router Tests
# ---------------------------------------------------------------------------

class TestAnalyticsRouter:

    def test_overview_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.get_workforce_overview.return_value = {
            "factory_id": str(FACTORY_1),
            "total_users": 10,
            "active_workers": 8,
            "inactive_workers": 2,
            "invited_users": 0,
            "disabled_users": 0,
            "by_role": {"factory_admin": 1, "factory_manager": 2, "safety_supervisor": 5},
        }
        test_app.dependency_overrides[get_workforce_analytics_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/analytics/overview", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["data"]["total_users"] == 10
            assert body["meta"]["factory_id"] == str(FACTORY_1)
        finally:
            test_app.dependency_overrides.clear()

    def test_attendance_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.get_attendance_metrics.return_value = {
            "factory_id": str(FACTORY_1),
            "active_workers": 5,
            "recorded_activities": 25,
        }
        test_app.dependency_overrides[get_workforce_analytics_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/analytics/attendance", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["data"]["active_workers"] == 5
        finally:
            test_app.dependency_overrides.clear()

    def test_incidents_analytics_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.get_incident_analytics.return_value = {
            "total_incidents": 12,
            "resolved_count": 10,
            "resolution_rate": 83.3,
        }
        test_app.dependency_overrides[get_workforce_analytics_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/analytics/incidents", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["total_incidents"] == 12
        finally:
            test_app.dependency_overrides.clear()

    def test_productivity_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.get_productivity_metrics.return_value = {
            "workers_evaluated": 6,
            "high_performers": 4,
            "low_performers": 1,
        }
        test_app.dependency_overrides[get_workforce_analytics_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/analytics/productivity", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["high_performers"] == 4
        finally:
            test_app.dependency_overrides.clear()

    def test_camera_coverage_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.get_camera_coverage.return_value = {
            "coverage_percentage": 98.5,
            "total_cameras": 8,
            "total_gaps": 2,
        }
        test_app.dependency_overrides[get_workforce_analytics_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/analytics/camera-coverage?period_hours=24", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["coverage_percentage"] == 98.5
        finally:
            test_app.dependency_overrides.clear()

    def test_summary_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.get_workforce_summary.return_value = {
            "factory_id": str(FACTORY_1),
            "overview": {"total_users": 10},
            "incidents": {"total_incidents": 12},
            "camera_coverage": {"coverage_percentage": 98.5},
        }
        test_app.dependency_overrides[get_workforce_analytics_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/analytics/summary", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert "overview" in resp.json()["data"]
        finally:
            test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 2. Assistant Router Tests
# ---------------------------------------------------------------------------

class TestAssistantRouter:

    def test_ask_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "answer": "Safety helmet is required in Zone B.",
            "conversation_id": "conv-123",
            "has_sufficient_evidence": True,
            "citations": [],
            "suggested_actions": [],
            "language": "en",
        }
        mock_svc.ask.return_value = mock_response
        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: mock_svc
        try:
            payload = {
                "question": "What PPE is required in Zone B?",
                "conversation_id": "conv-123",
                "language_preference": "en",
            }
            resp = client.post("/api/v1/assistant/ask", json=payload, headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert "helmet" in body["data"]["answer"]
        finally:
            test_app.dependency_overrides.clear()

    def test_sources_endpoint(self, client, test_app):
        mock_svc = MagicMock()
        citation_mock = MagicMock()
        citation_mock.model_dump.return_value = {
            "source_title": "Factory Safety Manual",
            "source_type": "manual_pdf",
            "source_id": "doc-01",
            "snippet": "All workers must wear hard hats.",
        }
        mock_svc.get_sources.return_value = [citation_mock]
        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/assistant/sources?q=helmet", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 1
        finally:
            test_app.dependency_overrides.clear()

    def test_clear_conversation(self, client, test_app):
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        auth_user = AuthenticatedUser(
            user_id=user_id,
            factory_id=FACTORY_1,
            role="factory_admin",
            full_name="Test Admin",
        )
        mock_svc = MagicMock()
        mock_svc.clear_conversation.return_value = True
        test_app.dependency_overrides[get_current_user_context] = lambda: auth_user
        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: mock_svc
        try:
            resp = client.delete("/api/v1/assistant/conversations/conv-123", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["cleared"] is True
            mock_svc.clear_conversation.assert_called_once_with(
                "conv-123",
                factory_id=FACTORY_1,
                user_id=user_id,
            )
        finally:
            test_app.dependency_overrides.clear()

    def test_clear_conversation_cross_user_or_factory_rejected(self, client, test_app):
        user_id = UUID("22222222-2222-2222-2222-222222222222")
        auth_user = AuthenticatedUser(
            user_id=user_id,
            factory_id=FACTORY_2,
            role="factory_admin",
            full_name="Other Factory User",
        )
        mock_svc = MagicMock()
        mock_svc.clear_conversation.side_effect = PermissionError(
            "Access denied: conversation 'conv-123' belongs to another user or factory."
        )
        test_app.dependency_overrides[get_current_user_context] = lambda: auth_user
        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: mock_svc
        try:
            resp = client.delete("/api/v1/assistant/conversations/conv-123", headers={"X-Factory-Id": str(FACTORY_2)})
            assert resp.status_code == 403
            assert resp.json()["error_code"] == "TENANT_ACCESS_DENIED"
            mock_svc.clear_conversation.assert_called_once_with(
                "conv-123",
                factory_id=FACTORY_2,
                user_id=user_id,
            )
        finally:
            test_app.dependency_overrides.clear()

    def test_clear_conversation_strict_signature_contract(self, client, test_app):
        """Ensure router matches OperixAssistantService.clear_conversation(conversation_id, factory_id, user_id) without permissive MagicMock."""
        owner_uid = UUID("11111111-1111-1111-1111-111111111111")
        other_uid = UUID("22222222-2222-2222-2222-222222222222")

        class _StrictOwnershipError(PermissionError):
            pass

        class _StrictAssistantStub:
            def __init__(self) -> None:
                self.calls: list[tuple[str, UUID | str | None, UUID | str | None]] = []

            def clear_conversation(
                self,
                conversation_id: str,
                factory_id: UUID | str | None = None,
                user_id: UUID | str | None = None,
            ) -> bool:
                if factory_id is None or user_id is None:
                    raise _StrictOwnershipError("factory_id and user_id are required")
                self.calls.append((conversation_id, factory_id, user_id))
                if (factory_id, user_id) != (FACTORY_1, owner_uid):
                    raise _StrictOwnershipError("Access denied: conversation belongs to another user or factory.")
                return True

        stub = _StrictAssistantStub()
        owner_user = AuthenticatedUser(user_id=owner_uid, factory_id=FACTORY_1, role="factory_admin", full_name="Owner")
        other_user = AuthenticatedUser(user_id=other_uid, factory_id=FACTORY_1, role="factory_admin", full_name="Other")

        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: stub
        try:
            test_app.dependency_overrides[get_current_user_context] = lambda: owner_user
            resp_ok = client.delete("/api/v1/assistant/conversations/conv-strict", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp_ok.status_code == 200
            assert resp_ok.json()["data"]["cleared"] is True

            test_app.dependency_overrides[get_current_user_context] = lambda: other_user
            resp_denied = client.delete("/api/v1/assistant/conversations/conv-strict", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp_denied.status_code == 403
            assert resp_denied.json()["error_code"] == "TENANT_ACCESS_DENIED"

            assert stub.calls == [
                ("conv-strict", FACTORY_1, owner_uid),
                ("conv-strict", FACTORY_1, other_uid),
            ]
        finally:
            test_app.dependency_overrides.clear()

    def test_assistant_health(self, client, test_app):
        mock_svc = MagicMock()
        mock_svc.check_health.return_value = {
            "status": "healthy",
            "llm_provider": "mock",
            "indexed_chunks": "42",
        }
        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/assistant/health", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["status"] == "healthy"
        finally:
            test_app.dependency_overrides.clear()

    def test_execute_action_endpoint(self, client, test_app):
        from app.services.ai_action_service import get_ai_action_service
        mock_action_svc = MagicMock()
        mock_action_svc.execute_action = AsyncMock(return_value={
            "action_id": "act-exec-01",
            "status": "executed",
            "message": "Maintenance ticket created",
            "audit_reference": "AUDIT-001",
            "details": {},
        })
        test_app.dependency_overrides[get_ai_action_service] = lambda: mock_action_svc
        try:
            payload = {
                "action_id": "act-exec-01",
                "action_type": "maintenance",
                "parameters": {"department": "Engineering"},
            }
            resp = client.post("/api/v1/assistant/actions/execute", json=payload, headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "success"
            assert body["data"]["status"] == "executed"
        finally:
            test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. Reports Router Tests
# ---------------------------------------------------------------------------

class TestReportsRouter:

    def test_generate_report(self, client, test_app):
        mock_svc = MagicMock()
        mock_meta = MagicMock()
        mock_meta.model_dump.return_value = {
            "report_id": "REP-20261124-001",
            "report_type": "comprehensive_safety",
            "format": "pdf",
            "factory_id": str(FACTORY_1),
            "file_name": "safety_report.pdf",
            "file_size_bytes": 1024,
        }
        mock_svc.generate_report.return_value = mock_meta
        test_app.dependency_overrides[get_reports_service_dep] = lambda: mock_svc
        try:
            payload = {
                "report_type": "comprehensive_safety",
                "format": "pdf",
            }
            resp = client.post("/api/v1/reports/generate", json=payload, headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 201
            assert resp.json()["data"]["report_id"] == "REP-20261124-001"
        finally:
            test_app.dependency_overrides.clear()

    def test_list_reports(self, client, test_app):
        mock_svc = MagicMock()
        mock_meta = MagicMock()
        mock_meta.model_dump.return_value = {
            "report_id": "REP-01",
            "factory_id": str(FACTORY_1),
        }
        mock_svc.list_reports.return_value = [mock_meta]
        test_app.dependency_overrides[get_reports_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/reports", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 1
        finally:
            test_app.dependency_overrides.clear()

    def test_get_report_cross_factory_denial(self, client, test_app):
        mock_svc = MagicMock()
        mock_meta = MagicMock()
        mock_meta.factory_id = FACTORY_2  # Belongs to factory 2
        mock_svc.get_report.return_value = mock_meta
        test_app.dependency_overrides[get_reports_service_dep] = lambda: mock_svc
        try:
            # Factory 1 attempts to read Factory 2's report
            resp = client.get("/api/v1/reports/REP-02", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 403
            assert resp.json()["status"] == "error"
        finally:
            test_app.dependency_overrides.clear()

    def test_download_report_path_traversal_protection(self, client, test_app, tmp_path):
        mock_svc = MagicMock()
        mock_meta = MagicMock()
        mock_meta.factory_id = FACTORY_1
        mock_meta.file_name = "secret.txt"
        mock_meta.mime_type = "text/plain"
        # Path outside storage dir
        mock_svc.get_report.return_value = mock_meta
        mock_svc.get_report_file_path.return_value = tmp_path / "evil" / ".." / "outside.txt"
        test_app.dependency_overrides[get_reports_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/reports/REP-EVIL/download", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 403
        finally:
            test_app.dependency_overrides.clear()

    def test_get_and_download_report_strict_signature_contract(self, client, test_app, tmp_path):
        """Ensure router matches ReportService.get_report(report_id, factory_id) and get_report_file_path(report_id, factory_id) without permissive MagicMock."""
        report_dir = tmp_path / str(FACTORY_1)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "comprehensive_safety_REP-STRICT.pdf"
        report_file.write_bytes(b"%PDF-1.4\n%strict-contract-test\n")

        class _StrictMeta:
            factory_id = FACTORY_1
            file_name = report_file.name
            mime_type = "application/pdf"

            def model_dump(self, mode: str = "json") -> dict:
                return {
                    "report_id": "REP-STRICT",
                    "factory_id": str(self.factory_id),
                    "file_name": self.file_name,
                    "mime_type": self.mime_type,
                }

        class _StrictReportStub:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, UUID]] = []

            def get_report(self, report_id: str, factory_id: UUID) -> _StrictMeta:
                self.calls.append(("get_report", report_id, factory_id))
                return _StrictMeta()

            def get_report_file_path(self, report_id: str, factory_id: UUID) -> Path:
                self.calls.append(("get_report_file_path", report_id, factory_id))
                return report_file

        stub = _StrictReportStub()
        auth_user = AuthenticatedUser(
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
            factory_id=FACTORY_1,
            role="factory_admin",
            full_name="Report Admin",
        )
        test_app.dependency_overrides[get_current_user_context] = lambda: auth_user
        test_app.dependency_overrides[get_reports_service_dep] = lambda: stub
        try:
            with patch("app.api.v1.endpoints.reports.get_reports_storage_path", return_value=tmp_path):
                resp_meta = client.get("/api/v1/reports/REP-STRICT", headers={"X-Factory-Id": str(FACTORY_1)})
                assert resp_meta.status_code == 200
                assert resp_meta.json()["data"]["report_id"] == "REP-STRICT"

                resp_dl = client.get("/api/v1/reports/REP-STRICT/download", headers={"X-Factory-Id": str(FACTORY_1)})
                assert resp_dl.status_code == 200
                assert resp_dl.content.startswith(b"%PDF-1.4")

            assert stub.calls == [
                ("get_report", "REP-STRICT", FACTORY_1),
                ("get_report", "REP-STRICT", FACTORY_1),
                ("get_report_file_path", "REP-STRICT", FACTORY_1),
            ]
        finally:
            test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 4. Incident Evidence Router Tests
# ---------------------------------------------------------------------------

class TestEvidenceRouter:

    def test_upload_evidence_json_base64(self, client, test_app):
        mock_svc = MagicMock()
        mock_rec = MagicMock()
        mock_rec.model_dump.return_value = {
            "id": str(uuid4()),
            "factory_id": str(FACTORY_1),
            "event_id": str(uuid4()),
            "kind": "snapshot",
            "storage_key": f"f/{FACTORY_1}/snap.jpg",
            "size_bytes": 12,
            "sha256": "abcdef123456",
        }
        mock_svc.upload.return_value = mock_rec
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            dummy_bytes = b"fake-jpeg-data"
            payload = {
                "event_id": str(uuid4()),
                "kind": "snapshot",
                "file_base64": base64.b64encode(dummy_bytes).decode(),
                "content_type": "image/jpeg",
            }
            resp = client.post("/api/v1/evidence/upload", json=payload, headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 201
            assert resp.json()["status"] == "success"
        finally:
            test_app.dependency_overrides.clear()

    def test_get_evidence_metadata(self, client, test_app):
        mock_svc = MagicMock()
        mock_meta = MagicMock()
        mock_meta.model_dump.return_value = {
            "id": str(uuid4()),
            "factory_id": str(FACTORY_1),
            "kind": "snapshot",
        }
        mock_svc.get_metadata.return_value = mock_meta
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            eid = uuid4()
            resp = client.get(f"/api/v1/evidence/{eid}", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["status"] == "success"
        finally:
            test_app.dependency_overrides.clear()

    def test_download_evidence(self, client, test_app):
        mock_svc = MagicMock()
        mock_rec = MagicMock()
        mock_rec.storage_key = "f/test/snap.jpg"
        mock_rec.content_type = "image/jpeg"
        mock_svc.download.return_value = (b"image-data", mock_rec)
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            eid = uuid4()
            resp = client.get(f"/api/v1/evidence/{eid}/download", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.content == b"image-data"
            assert resp.headers["content-type"] == "image/jpeg"
        finally:
            test_app.dependency_overrides.clear()

    def test_verify_evidence_integrity(self, client, test_app):
        mock_svc = MagicMock()
        mock_res = MagicMock()
        mock_res.model_dump.return_value = {
            "evidence_id": str(uuid4()),
            "is_valid": True,
            "calculated_sha256": "abcdef",
            "recorded_sha256": "abcdef",
        }
        mock_svc.verify_integrity.return_value = mock_res
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            eid = uuid4()
            resp = client.post(f"/api/v1/evidence/{eid}/verify-integrity", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["is_valid"] is True
        finally:
            test_app.dependency_overrides.clear()

    def test_upload_evidence_invalid_base64(self, client, test_app):
        mock_svc = MagicMock()
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            payload = {
                "event_id": str(uuid4()),
                "kind": "snapshot",
                "file_base64": "!!!not-valid-base64???",
                "content_type": "image/jpeg",
            }
            resp = client.post("/api/v1/evidence/upload", json=payload, headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 400
            assert resp.json()["status"] == "error"
        finally:
            test_app.dependency_overrides.clear()

    def test_list_evidence_filtered_by_event(self, client, test_app):
        mock_svc = MagicMock()
        mock_rec = MagicMock()
        mock_rec.model_dump.return_value = {"id": str(uuid4()), "event_id": str(uuid4())}
        mock_svc.list_by_event.return_value = [mock_rec]
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            eid = uuid4()
            resp = client.get(f"/api/v1/evidence?event_id={eid}", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 1
        finally:
            test_app.dependency_overrides.clear()

    def test_list_evidence_filtered_by_incident(self, client, test_app):
        mock_svc = MagicMock()
        mock_rec = MagicMock()
        mock_rec.model_dump.return_value = {"id": str(uuid4()), "incident_id": str(uuid4())}
        mock_svc.list_by_incident.return_value = [mock_rec]
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            inc_id = uuid4()
            resp = client.get(f"/api/v1/evidence?incident_id={inc_id}", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert len(resp.json()["data"]) == 1
        finally:
            test_app.dependency_overrides.clear()

    def test_list_evidence_paginated(self, client, test_app):
        mock_svc = MagicMock()
        mock_page = MagicMock()
        mock_page.model_dump.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
        }
        mock_svc.list_by_factory.return_value = mock_page
        test_app.dependency_overrides[get_evidence_service_dep] = lambda: mock_svc
        try:
            resp = client.get("/api/v1/evidence?page=1&page_size=20", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert "items" in resp.json()["data"]
        finally:
            test_app.dependency_overrides.clear()
