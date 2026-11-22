"""
reports_generation/tests/test_pdf_generator.py
Tests for PDFReportGenerator — verifies that real PDF files are created on disk.
Uses tempdir; no DB connection.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

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


class TestPDFGeneratorWorkforce(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.pdf_generator import PDFReportGenerator
        self.gen = PDFReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_workforce_pdf_created(self):
        out = Path(self.tmp) / "workforce_test.pdf"
        self.gen.generate_workforce_pdf(_make_workforce(), out)
        self.assertTrue(out.exists(), "PDF file was not created")
        self.assertGreater(out.stat().st_size, 100, "PDF file is too small")

    def test_workforce_pdf_starts_with_pdf_magic(self):
        out = Path(self.tmp) / "workforce_magic.pdf"
        self.gen.generate_workforce_pdf(_make_workforce(), out)
        with open(out, "rb") as f:
            header = f.read(4)
        self.assertEqual(header, b"%PDF", "File does not start with %PDF magic bytes")


class TestPDFGeneratorIncident(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.pdf_generator import PDFReportGenerator
        self.gen = PDFReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_incident_pdf_created(self):
        out = Path(self.tmp) / "incident_test.pdf"
        self.gen.generate_incident_pdf(_make_incident(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)

    def test_incident_pdf_magic_bytes(self):
        out = Path(self.tmp) / "incident_magic.pdf"
        self.gen.generate_incident_pdf(_make_incident(), out)
        with open(out, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")


class TestPDFGeneratorCameraCoverage(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.pdf_generator import PDFReportGenerator
        self.gen = PDFReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_camera_pdf_created(self):
        out = Path(self.tmp) / "camera_test.pdf"
        self.gen.generate_camera_coverage_pdf(_make_camera(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)


class TestPDFGeneratorComprehensive(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from reports_generation.generators.pdf_generator import PDFReportGenerator
        self.gen = PDFReportGenerator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_comprehensive_pdf_created(self):
        out = Path(self.tmp) / "comprehensive_test.pdf"
        self.gen.generate_comprehensive_safety_pdf(_make_comprehensive(), out)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)

    def test_comprehensive_pdf_magic_bytes(self):
        out = Path(self.tmp) / "comp_magic.pdf"
        self.gen.generate_comprehensive_safety_pdf(_make_comprehensive(), out)
        with open(out, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")


if __name__ == "__main__":
    unittest.main()
