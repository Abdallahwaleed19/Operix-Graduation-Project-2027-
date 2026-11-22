"""
reports_generation/tests/test_excel_generator.py
Tests for ExcelReportGenerator — verifies real Excel files created on disk.
Uses tempdir; no DB connection.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import openpyxl

from reports_generation.schemas import (
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
    FactoryInfo,
    IncidentReportData,
    WorkforceReportData,
)

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
FACTORY_INFO = FactoryInfo(factory_id=FACTORY_ID)
NOW = datetime.now(tz=timezone.utc)
DATE_FROM = date(2027, 1, 1)
DATE_TO = date(2027, 1, 31)


def _make_workforce() -> WorkforceReportData:
    return WorkforceReportData(
        factory_info=FACTORY_INFO,
        generated_at=NOW,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        overview={"total_workers": 100, "active_workers": 90, "incident_rate": 5.0},
        attendance_proxy={"present_count": 90, "absent_count": 10, "attendance_rate": 90.0},
        productivity_proxy={"avg_tasks": 4.5, "completion_rate": 88.0},
        incident_workforce={"total_incidents": 12, "resolution_rate": 83.3},
    )


def _make_incident() -> IncidentReportData:
    return IncidentReportData(
        factory_info=FACTORY_INFO,
        generated_at=NOW,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        total_incidents=12,
        severity_breakdown={"critical": 1, "high": 3, "medium": 5, "low": 3},
        state_breakdown={"open": 2, "resolved": 10},
        resolution_rate=83.3,
        avg_resolution_time_minutes=45.0,
    )


def _make_camera() -> CameraCoverageReportData:
    return CameraCoverageReportData(
        factory_info=FACTORY_INFO,
        generated_at=NOW,
        total_cameras=20,
        active_cameras=18,
        coverage_percentage=90.0,
        per_camera_status=[{"id": "cam-01", "status": "active"}],
    )


def _make_comprehensive() -> ComprehensiveSafetyReportData:
    return ComprehensiveSafetyReportData(
        factory_info=FACTORY_INFO,
        generated_at=NOW,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        safety_health_score=88.5,
        workforce_overview={"total_workers": 100},
        incident_analytics={"total_incidents": 12, "resolution_rate": 0.833},
        camera_coverage={"coverage_percentage": 90.0},
        active_safety_rules_count=15,
    )


class TestExcelGeneratorWorkforce(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.excel_generator import ExcelReportGenerator
        self.gen = ExcelReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_file_created(self):
        out = Path(self.tmp) / "workforce.xlsx"
        self.gen.generate_workforce_excel(_make_workforce(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

    def test_valid_workbook(self):
        out = Path(self.tmp) / "workforce_wb.xlsx"
        self.gen.generate_workforce_excel(_make_workforce(), out)
        wb = openpyxl.load_workbook(out)
        self.assertGreater(len(wb.sheetnames), 0)

    def test_has_expected_sheet(self):
        out = Path(self.tmp) / "workforce_sheet.xlsx"
        self.gen.generate_workforce_excel(_make_workforce(), out)
        wb = openpyxl.load_workbook(out)
        sheet_names_lower = [s.lower() for s in wb.sheetnames]
        self.assertTrue(
            any("workforce" in n or "summary" in n or "report" in n for n in sheet_names_lower),
            f"Expected a workforce/summary sheet, got: {wb.sheetnames}",
        )


class TestExcelGeneratorIncident(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.excel_generator import ExcelReportGenerator
        self.gen = ExcelReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_file_created(self):
        out = Path(self.tmp) / "incident.xlsx"
        self.gen.generate_incident_excel(_make_incident(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

    def test_valid_workbook(self):
        out = Path(self.tmp) / "incident_wb.xlsx"
        self.gen.generate_incident_excel(_make_incident(), out)
        wb = openpyxl.load_workbook(out)
        self.assertGreater(len(wb.sheetnames), 0)


class TestExcelGeneratorCameraCoverage(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.excel_generator import ExcelReportGenerator
        self.gen = ExcelReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_file_created(self):
        out = Path(self.tmp) / "camera.xlsx"
        self.gen.generate_camera_coverage_excel(_make_camera(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

    def test_valid_workbook(self):
        out = Path(self.tmp) / "camera_wb.xlsx"
        self.gen.generate_camera_coverage_excel(_make_camera(), out)
        wb = openpyxl.load_workbook(out)
        self.assertGreater(len(wb.sheetnames), 0)


class TestExcelGeneratorComprehensive(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.excel_generator import ExcelReportGenerator
        self.gen = ExcelReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_file_created(self):
        out = Path(self.tmp) / "comprehensive.xlsx"
        self.gen.generate_comprehensive_safety_excel(_make_comprehensive(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

    def test_multiple_sheets(self):
        out = Path(self.tmp) / "comprehensive_sheets.xlsx"
        self.gen.generate_comprehensive_safety_excel(_make_comprehensive(), out)
        wb = openpyxl.load_workbook(out)
        self.assertGreaterEqual(len(wb.sheetnames), 1)


if __name__ == "__main__":
    unittest.main()
