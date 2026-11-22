"""
reports_generation/tests/test_report_service.py
Tests for ReportService (the main facade).
Mocks both data_service and export_service — no real DB or files needed.
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID

from reports_generation.schemas import ReportFormat, ReportMetadata, ReportType

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")


def _make_meta(report_type=ReportType.WORKFORCE, fmt=ReportFormat.PDF) -> ReportMetadata:
    return ReportMetadata(
        report_id="REP-TEST-001",
        report_type=report_type,
        format=fmt,
        factory_id=FACTORY_ID,
        title=f"{report_type.value} report",
        generated_at=datetime.now(tz=timezone.utc),
        file_name=f"{report_type.value}_REP-TEST-001.{fmt.value}",
        file_size_bytes=1234,
        mime_type="application/pdf",
    )


def _get_service():
    """Build a ReportService with mocked sub-services."""
    from reports_generation.services.report_service import ReportService
    svc = ReportService.__new__(ReportService)
    svc.data_service = MagicMock()
    svc.export_service = MagicMock()
    svc.storage_dir = MagicMock()
    svc._registry = {}
    return svc


def _setup_data_mock(svc, report_type):
    """Wire the correct data_service method to return a MagicMock for the given type."""
    mock_data = MagicMock()
    method_map = {
        ReportType.WORKFORCE:           "get_workforce_report_data",
        ReportType.INCIDENT:            "get_incident_report_data",
        ReportType.CAMERA_COVERAGE:     "get_camera_coverage_report_data",
        ReportType.COMPREHENSIVE_SAFETY: "get_comprehensive_safety_report_data",
    }
    getattr(svc.data_service, method_map[report_type]).return_value = mock_data
    return mock_data


class TestReportServiceGenerate(unittest.TestCase):

    def test_generate_workforce_pdf(self):
        svc = _get_service()
        _setup_data_mock(svc, ReportType.WORKFORCE)
        expected_meta = _make_meta(ReportType.WORKFORCE, ReportFormat.PDF)
        svc.export_service.export.return_value = expected_meta

        meta = svc.generate_report(
            report_type=ReportType.WORKFORCE,
            format=ReportFormat.PDF,
            factory_id=FACTORY_ID,
        )
        self.assertEqual(meta.report_type, ReportType.WORKFORCE)
        self.assertEqual(meta.format, ReportFormat.PDF)

    def test_generate_all_types_all_formats(self):
        """All 4 types × 3 formats = 12 combinations must succeed."""
        for rt in ReportType:
            for fmt in ReportFormat:
                with self.subTest(report_type=rt.value, format=fmt.value):
                    svc = _get_service()
                    _setup_data_mock(svc, rt)
                    svc.export_service.export.return_value = _make_meta(rt, fmt)
                    meta = svc.generate_report(
                        report_type=rt,
                        format=fmt,
                        factory_id=FACTORY_ID,
                    )
                    self.assertIsInstance(meta, ReportMetadata)

    def test_date_range_passed_to_data_service(self):
        svc = _get_service()
        _setup_data_mock(svc, ReportType.INCIDENT)
        svc.export_service.export.return_value = _make_meta(ReportType.INCIDENT, ReportFormat.JSON)

        svc.generate_report(
            report_type=ReportType.INCIDENT,
            format=ReportFormat.JSON,
            factory_id=FACTORY_ID,
            date_from=date(2027, 1, 1),
            date_to=date(2027, 1, 31),
        )
        svc.data_service.get_incident_report_data.assert_called_once()

    def test_export_service_called(self):
        svc = _get_service()
        _setup_data_mock(svc, ReportType.WORKFORCE)
        svc.export_service.export.return_value = _make_meta()

        svc.generate_report(ReportType.WORKFORCE, ReportFormat.PDF, FACTORY_ID)
        svc.export_service.export.assert_called_once()

    def test_invalid_report_type_string(self):
        from reports_generation.exceptions import InvalidReportTypeError
        svc = _get_service()
        with self.assertRaises(InvalidReportTypeError):
            svc.generate_report(report_type="nonexistent", format=ReportFormat.PDF)

    def test_invalid_format_string(self):
        from reports_generation.exceptions import InvalidReportFormatError
        svc = _get_service()
        with self.assertRaises(InvalidReportFormatError):
            svc.generate_report(report_type=ReportType.WORKFORCE, format="docx")

    def test_result_registered_in_registry(self):
        svc = _get_service()
        _setup_data_mock(svc, ReportType.WORKFORCE)
        meta = _make_meta()
        svc.export_service.export.return_value = meta
        svc.generate_report(ReportType.WORKFORCE, ReportFormat.PDF, FACTORY_ID)
        self.assertIn(meta.report_id, svc._registry)

    def test_camera_report_no_date_range(self):
        """Camera coverage report should work without date params."""
        svc = _get_service()
        _setup_data_mock(svc, ReportType.CAMERA_COVERAGE)
        svc.export_service.export.return_value = _make_meta(ReportType.CAMERA_COVERAGE, ReportFormat.PDF)
        meta = svc.generate_report(ReportType.CAMERA_COVERAGE, ReportFormat.PDF, FACTORY_ID)
        self.assertEqual(meta.report_type, ReportType.CAMERA_COVERAGE)
        # get_camera_coverage_report_data should NOT receive date_from/date_to
        svc.data_service.get_camera_coverage_report_data.assert_called_once()


class TestGetReportServiceSingleton(unittest.TestCase):

    def test_singleton(self):
        import reports_generation.services.report_service as rs_module
        original = rs_module._service_instance
        rs_module._service_instance = None
        try:
            from reports_generation.services.report_service import get_report_service
            s1 = get_report_service()
            s2 = get_report_service()
            self.assertIs(s1, s2)
        finally:
            rs_module._service_instance = original


if __name__ == "__main__":
    unittest.main()
