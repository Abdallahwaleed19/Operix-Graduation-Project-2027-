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
        mock_svc = MagicMock()
        mock_svc.clear_conversation.return_value = True
        test_app.dependency_overrides[get_llm_assistant_service_dep] = lambda: mock_svc
        try:
            resp = client.delete("/api/v1/assistant/conversations/conv-123", headers={"X-Factory-Id": str(FACTORY_1)})
            assert resp.status_code == 200
            assert resp.json()["data"]["cleared"] is True
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
