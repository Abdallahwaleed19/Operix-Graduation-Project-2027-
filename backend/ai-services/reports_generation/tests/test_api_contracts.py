"""
reports_generation/tests/test_api_contracts.py
Tests for the Pydantic request and response contracts.
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from uuid import UUID

from reports_generation.api_contracts.requests import GenerateReportRequest, ReportFilterParams
from reports_generation.api_contracts.responses import (
    ErrorResponse,
    GenerateReportResponse,
    ReportDownloadResponse,
    ReportListResponse,
)
from reports_generation.schemas import (
    ReportFormat,
    ReportMetadata,
    ReportType,
)

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")


def _make_metadata(report_type=ReportType.WORKFORCE, fmt=ReportFormat.PDF) -> ReportMetadata:
    return ReportMetadata(
        report_id="REP-20270101-ABCDEF",
        report_type=report_type,
        format=fmt,
        factory_id=FACTORY_ID,
        title="Workforce Report",
        generated_at=datetime.now(tz=timezone.utc),
        file_name="workforce_REP-20270101-ABCDEF.pdf",
        file_size_bytes=12345,
        mime_type="application/pdf",
    )


class TestGenerateReportRequest(unittest.TestCase):

    def test_valid_minimal(self):
        """factory_id is optional — only report_type required."""
        req = GenerateReportRequest(report_type=ReportType.WORKFORCE)
        self.assertEqual(req.report_type, ReportType.WORKFORCE)
        self.assertEqual(req.format, ReportFormat.PDF)  # default

    def test_valid_with_factory_id(self):
        req = GenerateReportRequest(
            report_type=ReportType.WORKFORCE,
            format=ReportFormat.PDF,
            factory_id=FACTORY_ID,
        )
        self.assertEqual(req.factory_id, FACTORY_ID)

    def test_valid_with_dates(self):
        req = GenerateReportRequest(
            report_type=ReportType.INCIDENT,
            format=ReportFormat.EXCEL,
            date_from=date(2027, 1, 1),
            date_to=date(2027, 1, 31),
        )
        self.assertEqual(req.date_from, date(2027, 1, 1))
        self.assertEqual(req.date_to, date(2027, 1, 31))

    def test_all_report_types(self):
        for rt in ReportType:
            req = GenerateReportRequest(report_type=rt)
            self.assertEqual(req.report_type, rt)

    def test_all_formats(self):
        for fmt in ReportFormat:
            req = GenerateReportRequest(report_type=ReportType.WORKFORCE, format=fmt)
            self.assertEqual(req.format, fmt)

    def test_invalid_report_type_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            GenerateReportRequest(report_type="invalid_type")

    def test_invalid_format_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            GenerateReportRequest(report_type=ReportType.WORKFORCE, format="docx")

    def test_missing_report_type_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            GenerateReportRequest()


class TestReportFilterParams(unittest.TestCase):

    def test_all_optional_defaults(self):
        params = ReportFilterParams()
        self.assertIsNone(params.report_type)
        self.assertIsNone(params.format)
        self.assertIsNone(params.factory_id)

    def test_with_values(self):
        params = ReportFilterParams(
            report_type=ReportType.WORKFORCE,
            format=ReportFormat.PDF,
            factory_id=FACTORY_ID,
        )
        self.assertEqual(params.report_type, ReportType.WORKFORCE)
        self.assertEqual(params.factory_id, FACTORY_ID)


class TestGenerateReportResponse(unittest.TestCase):

    def test_construction(self):
        meta = _make_metadata()
        resp = GenerateReportResponse(data=meta)
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.report_id, "REP-20270101-ABCDEF")

    def test_json_roundtrip(self):
        meta = _make_metadata()
        resp = GenerateReportResponse(data=meta)
        raw = resp.model_dump_json()
        restored = GenerateReportResponse.model_validate_json(raw)
        self.assertEqual(restored.data.report_id, resp.data.report_id)

    def test_custom_message(self):
        meta = _make_metadata()
        resp = GenerateReportResponse(data=meta, message="Custom message.")
        self.assertEqual(resp.message, "Custom message.")

    def test_all_report_types_in_response(self):
        for rt in ReportType:
            for fmt in ReportFormat:
                meta = _make_metadata(rt, fmt)
                resp = GenerateReportResponse(data=meta)
                self.assertEqual(resp.data.report_type, rt)


class TestReportListResponse(unittest.TestCase):

    def test_empty_list(self):
        resp = ReportListResponse(total=0, data=[])
        self.assertEqual(resp.total, 0)
        self.assertEqual(len(resp.data), 0)

    def test_with_items(self):
        metas = [_make_metadata(rt) for rt in ReportType]
        resp = ReportListResponse(total=len(metas), data=metas)
        self.assertEqual(resp.total, len(list(ReportType)))

    def test_pagination_defaults(self):
        resp = ReportListResponse(total=0, data=[])
        self.assertEqual(resp.page, 1)
        self.assertEqual(resp.page_size, 20)


class TestReportDownloadResponse(unittest.TestCase):

    def test_construction(self):
        resp = ReportDownloadResponse(
            report_id="REP-X",
            file_name="workforce_REP-X.pdf",
            file_path="/storage/reports/workforce_REP-X.pdf",
            mime_type="application/pdf",
            file_size_bytes=99999,
        )
        self.assertEqual(resp.report_id, "REP-X")
        self.assertEqual(resp.mime_type, "application/pdf")


class TestErrorResponse(unittest.TestCase):

    def test_construction(self):
        err = ErrorResponse(error_code="NOT_FOUND", message="Report not found.")
        self.assertFalse(err.success)
        self.assertEqual(err.error_code, "NOT_FOUND")
        self.assertIsNone(err.detail)

    def test_with_detail(self):
        err = ErrorResponse(
            error_code="EXPORT_FAILED",
            message="Export failed.",
            detail="Disk full.",
        )
        self.assertEqual(err.detail, "Disk full.")


if __name__ == "__main__":
    unittest.main()
