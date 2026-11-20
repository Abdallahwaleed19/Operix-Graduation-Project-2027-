"""
workforce_analytics/tests/test_service.py
Automated tests for WorkforceAnalyticsService and API Contracts.

Covers:
  - Service initialization & factory resolution
  - Health check
  - Each individual analytics service operation
  - Unified summary operation
  - JSON serialization via Pydantic model_dump
  - API envelope validation
  - API request contract validation (date ranges, threshold checks)
  - Edge cases (database errors, empty datasets, invalid filters)
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from pydantic import ValidationError

from ..api_contracts.requests import (
    AttendanceQueryRequest,
    CameraCoverageQueryRequest,
    IncidentQueryRequest,
    ProductivityQueryRequest,
    SummaryQueryRequest,
    WorkforceQueryRequest,
)
from ..api_contracts.responses import (
    APIErrorResponse,
    APIResponse,
    WorkforceSummaryResponse,
)
from ..database import test_connection
from ..schemas import (
    AttendanceMetrics,
    CameraCoverage,
    IncidentAnalytics,
    ProductivityMetrics,
    WorkforceOverview,
    WorkforceSummary,
)
from ..services.analytics_service import WorkforceAnalyticsService

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")


class TestWorkforceAnalyticsService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_available = test_connection()
        cls.service = WorkforceAnalyticsService(default_factory_id=FACTORY_ID)

    def setUp(self):
        if not self.db_available:
            self.skipTest("Database not reachable")

    # 1. Health check
    def test_check_health(self):
        health = self.service.check_health()
        self.assertEqual(health["status"], "healthy")
        self.assertTrue(health["database_connected"])
        self.assertEqual(health["default_factory_id"], str(FACTORY_ID))

    # 2. Overview
    def test_get_workforce_overview_model(self):
        res = self.service.get_workforce_overview()
        self.assertIsInstance(res, WorkforceOverview)
        self.assertEqual(res.total_users, 8)
        self.assertEqual(res.active_workers, 7)

    def test_get_workforce_overview_as_dict(self):
        res = self.service.get_workforce_overview(as_dict=True)
        self.assertIsInstance(res, dict)
        self.assertIn("total_users", res)
        self.assertIn("by_role", res)

    # 3. Attendance
    def test_get_attendance_metrics(self):
        res = self.service.get_attendance_metrics()
        self.assertIsInstance(res, AttendanceMetrics)
        self.assertEqual(res.total_members, 8)
        self.assertGreaterEqual(res.activity_rate_pct, 0.0)

    def test_get_attendance_metrics_with_date_filter(self):
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=14)
        res = self.service.get_attendance_metrics(start_date=start, end_date=end)
        self.assertIsInstance(res, AttendanceMetrics)
        self.assertEqual(res.period_start, start)
        self.assertEqual(res.period_end, end)

    # 4. Incidents
    def test_get_incident_analytics(self):
        res = self.service.get_incident_analytics()
        self.assertIsInstance(res, IncidentAnalytics)
        self.assertEqual(res.total_incidents, 15)
        self.assertEqual(res.resolved_incidents, 7)

    def test_get_incident_analytics_as_dict(self):
        res = self.service.get_incident_analytics(as_dict=True)
        self.assertIsInstance(res, dict)
        self.assertEqual(res["total_incidents"], 15)
        self.assertEqual(res["resolved_incidents"], 7)

    # 5. Productivity
    def test_get_productivity_metrics(self):
        res = self.service.get_productivity_metrics()
        self.assertIsInstance(res, ProductivityMetrics)
        self.assertEqual(res.workers_analysed, 7)

    def test_get_productivity_metrics_custom_thresholds(self):
        res = self.service.get_productivity_metrics(low_threshold=1, high_threshold=3)
        self.assertEqual(res.thresholds_used, {"low": 1, "high": 3})

    # 6. Camera Coverage
    def test_get_camera_coverage(self):
        res = self.service.get_camera_coverage(period_hours=720.0)
        self.assertIsInstance(res, CameraCoverage)
        self.assertEqual(res.total_cameras, 4)
        self.assertEqual(res.active_cameras, 3)

    # 7. Summary
    def test_get_workforce_summary(self):
        res = self.service.get_workforce_summary()
        self.assertIsInstance(res, WorkforceSummary)
        self.assertIsNotNone(res.overview)
        self.assertIsNotNone(res.incidents)
        self.assertIsNotNone(res.productivity)

    def test_get_workforce_summary_as_dict_serializable(self):
        res = self.service.get_workforce_summary(as_dict=True)
        self.assertIsInstance(res, dict)
        # Verify JSON serializable without exception
        encoded = json.dumps(res, default=str)
        self.assertTrue(len(encoded) > 0)


class TestAPIContracts(unittest.TestCase):
    """Unit tests for API Contracts (Validation & Envelopes)."""

    def test_workforce_query_request_valid(self):
        req = WorkforceQueryRequest()
        self.assertIsNone(req.factory_id)
        req2 = WorkforceQueryRequest(factory_id=FACTORY_ID)
        self.assertEqual(req2.factory_id, FACTORY_ID)

    def test_attendance_query_request_valid_dates(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 10, tzinfo=timezone.utc)
        req = AttendanceQueryRequest(start_date=start, end_date=end)
        self.assertEqual(req.start_date, start)
        self.assertEqual(req.end_date, end)

    def test_attendance_query_request_invalid_date_range(self):
        start = datetime(2026, 1, 10, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            AttendanceQueryRequest(start_date=start, end_date=end)

    def test_incident_query_request_invalid_date_range(self):
        start = datetime(2026, 5, 20, tzinfo=timezone.utc)
        end = datetime(2026, 5, 10, tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            IncidentQueryRequest(start_date=start, end_date=end)

    def test_productivity_query_request_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            ProductivityQueryRequest(low_threshold=10, high_threshold=2)

    def test_productivity_query_request_negative_thresholds(self):
        with self.assertRaises(ValidationError):
            ProductivityQueryRequest(low_threshold=-1)

    def test_camera_coverage_query_request_invalid_period(self):
        with self.assertRaises(ValidationError):
            CameraCoverageQueryRequest(period_hours=0)
        with self.assertRaises(ValidationError):
            CameraCoverageQueryRequest(period_hours=-10)

    def test_summary_query_request_valid(self):
        req = SummaryQueryRequest(period_hours=48.0)
        self.assertEqual(req.period_hours, 48.0)

    def test_api_response_envelope_serialization(self):
        envelope = APIResponse(
            status="success",
            data={"test_metric": 42},
        )
        dumped = envelope.model_dump(mode="json")
        self.assertEqual(dumped["status"], "success")
        self.assertEqual(dumped["data"]["test_metric"], 42)
        self.assertIn("meta", dumped)

    def test_api_error_response_envelope(self):
        err = APIErrorResponse(
            error_code="INVALID_DATE_RANGE",
            message="start_date cannot be after end_date",
            details=[{"field": "start_date", "issue": "Must be <= end_date"}],
        )
        dumped = err.model_dump(mode="json")
        self.assertEqual(dumped["status"], "error")
        self.assertEqual(dumped["error_code"], "INVALID_DATE_RANGE")
        self.assertEqual(len(dumped["details"]), 1)


class TestServiceEdgeCases(unittest.TestCase):
    """Test error handling, mocked DB disconnects, and empty datasets."""

    def test_database_connection_failure_handling(self):
        service = WorkforceAnalyticsService()
        with patch("workforce_analytics.services.analytics_service.test_connection", return_value=False):
            health = service.check_health()
            self.assertEqual(health["status"], "unhealthy")
            self.assertFalse(health["database_connected"])

    def test_empty_dataset_in_service(self):
        service = WorkforceAnalyticsService()
        with patch("workforce_analytics.analytics.fetch_per_worker_productivity", return_value=[]):
            res = service.get_productivity_metrics()
            self.assertEqual(res.workers_analysed, 0)
            self.assertEqual(res.avg_handled_per_worker, 0.0)
            self.assertEqual(res.low_performers, [])
            self.assertEqual(res.high_performers, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
