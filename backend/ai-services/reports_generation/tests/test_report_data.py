"""
reports_generation/tests/test_report_data.py
Unit tests for ReportDataService.
Mocks WorkforceAnalyticsService and ReportRepository — no DB connection needed.
"""
from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

from reports_generation.schemas import (
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
    FactoryInfo,
    IncidentReportData,
    WorkforceReportData,
)

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")


def _make_analytics_mock():
    """Return a MagicMock that mimics WorkforceAnalyticsService."""
    m = MagicMock()

    # get_workforce_overview → overview-like object with .model_dump()
    overview = MagicMock()
    overview.model_dump.return_value = {
        "total_workers": 100,
        "active_workers": 90,
        "incident_rate": 5.0,
    }
    m.get_workforce_overview.return_value = overview

    # get_attendance_metrics
    attendance = MagicMock()
    attendance.model_dump.return_value = {
        "present_count": 90, "absent_count": 10, "attendance_rate": 90.0
    }
    m.get_attendance_metrics.return_value = attendance

    # get_productivity_metrics
    productivity = MagicMock()
    productivity.model_dump.return_value = {"avg_tasks": 4.5, "completion_rate": 88.0}
    m.get_productivity_metrics.return_value = productivity

    # get_incident_analytics
    inc_analytics = MagicMock()
    inc_analytics.model_dump.return_value = {
        "total_incidents": 12,
        "severity_breakdown": {"critical": 1},
        "state_breakdown": {"open": 2, "resolved": 10},
        "resolution_rate": 0.833,
        "avg_resolution_time_minutes": 45.0,
    }
    m.get_incident_analytics.return_value = inc_analytics

    # get_camera_coverage
    cam = MagicMock()
    cam.model_dump.return_value = {
        "total_cameras": 20,
        "active_cameras": 18,
        "coverage_percentage": 90.0,
        "per_camera_status": [],
    }
    m.get_camera_coverage.return_value = cam

    # get_workforce_summary
    summary = MagicMock()
    summary.model_dump.return_value = {
        "workforce": {"total_workers": 100},
        "incidents": {"total_incidents": 12, "resolution_rate": 0.833},
        "camera_coverage": {"coverage_percentage": 90.0},
    }
    m.get_workforce_summary.return_value = summary

    return m


def _make_repo_mock():
    m = MagicMock()
    m.get_factory_info.return_value = FactoryInfo(factory_id=FACTORY_ID)
    m.get_detailed_incidents.return_value = []
    m.get_unobserved_gaps.return_value = []
    m.get_active_safety_rules_count.return_value = 10
    return m


def _get_data_service():
    from reports_generation.services.report_data_service import ReportDataService
    svc = ReportDataService.__new__(ReportDataService)
    svc.analytics_service = _make_analytics_mock()
    svc.repository = _make_repo_mock()
    return svc


class TestReportDataServiceWorkforce(unittest.TestCase):

    def test_returns_correct_type(self):
        svc = _get_data_service()
        result = svc.get_workforce_report_data(FACTORY_ID)
        self.assertIsInstance(result, WorkforceReportData)

    def test_has_disclaimer(self):
        svc = _get_data_service()
        result = svc.get_workforce_report_data(FACTORY_ID)
        self.assertIn("proxy", result.disclaimer.lower())

    def test_with_date_range(self):
        svc = _get_data_service()
        result = svc.get_workforce_report_data(
            FACTORY_ID, date_from=date(2027, 1, 1), date_to=date(2027, 1, 31)
        )
        self.assertIsInstance(result, WorkforceReportData)
        self.assertEqual(result.date_from, date(2027, 1, 1))

    def test_invalid_date_range_raises(self):
        from reports_generation.exceptions import InvalidDateRangeError
        svc = _get_data_service()
        with self.assertRaises(InvalidDateRangeError):
            svc.get_workforce_report_data(
                FACTORY_ID,
                date_from=date(2027, 2, 1),
                date_to=date(2027, 1, 1),
            )


class TestReportDataServiceIncident(unittest.TestCase):

    def test_returns_correct_type(self):
        svc = _get_data_service()
        result = svc.get_incident_report_data(FACTORY_ID)
        self.assertIsInstance(result, IncidentReportData)

    def test_total_incidents(self):
        svc = _get_data_service()
        result = svc.get_incident_report_data(FACTORY_ID)
        self.assertEqual(result.total_incidents, 12)

    def test_with_date_range(self):
        svc = _get_data_service()
        result = svc.get_incident_report_data(
            FACTORY_ID, date_from=date(2027, 1, 1), date_to=date(2027, 1, 31)
        )
        self.assertIsInstance(result, IncidentReportData)


class TestReportDataServiceCameraCoverage(unittest.TestCase):

    def test_returns_correct_type(self):
        svc = _get_data_service()
        result = svc.get_camera_coverage_report_data(FACTORY_ID)
        self.assertIsInstance(result, CameraCoverageReportData)

    def test_camera_counts(self):
        svc = _get_data_service()
        result = svc.get_camera_coverage_report_data(FACTORY_ID)
        self.assertEqual(result.total_cameras, 20)
        self.assertEqual(result.active_cameras, 18)


class TestReportDataServiceComprehensive(unittest.TestCase):

    def test_returns_correct_type(self):
        svc = _get_data_service()
        result = svc.get_comprehensive_safety_report_data(FACTORY_ID)
        self.assertIsInstance(result, ComprehensiveSafetyReportData)

    def test_safety_score_in_range(self):
        svc = _get_data_service()
        result = svc.get_comprehensive_safety_report_data(FACTORY_ID)
        self.assertGreaterEqual(result.safety_health_score, 0.0)
        self.assertLessEqual(result.safety_health_score, 100.0)

    def test_active_rules_count(self):
        svc = _get_data_service()
        result = svc.get_comprehensive_safety_report_data(FACTORY_ID)
        self.assertEqual(result.active_safety_rules_count, 10)


if __name__ == "__main__":
    unittest.main()
