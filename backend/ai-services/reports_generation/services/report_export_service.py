"""
reports_generation/services/report_export_service.py
Renders and persists report artifacts to disk.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from ..config import REPORTS_STORAGE_DIR
from ..exceptions import InvalidReportFormatError, ReportExportError
from ..generators.excel_generator import ExcelReportGenerator
from ..generators.pdf_generator import PDFReportGenerator
from ..schemas import (
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
    IncidentReportData,
    ReportFormat,
    ReportMetadata,
    ReportType,
    WorkforceReportData,
)

ReportDataUnion = Union[
    WorkforceReportData,
    IncidentReportData,
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
]


class ReportExportService:
    """Dispatches report data to target rendering generator and writes artifact to disk."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        pdf_generator: Optional[PDFReportGenerator] = None,
        excel_generator: Optional[ExcelReportGenerator] = None,
    ) -> None:
        self.storage_dir = storage_dir or REPORTS_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_generator = pdf_generator or PDFReportGenerator()
        self.excel_generator = excel_generator or ExcelReportGenerator()

    def export(
        self,
        report_type: ReportType,
        export_format: ReportFormat,
        data: ReportDataUnion,
        factory_id: UUID,
    ) -> ReportMetadata:
        """Render data to requested format and return ReportMetadata."""
        report_id = f"REP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        file_ext = export_format.value
        filename = f"{report_type.value}_{report_id}.{file_ext}"
        target_path = self.storage_dir / filename

        mime_types = {
            ReportFormat.PDF: "application/pdf",
            ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ReportFormat.JSON: "application/json",
        }

        try:
            if export_format == ReportFormat.PDF:
                if report_type == ReportType.WORKFORCE:
                    self.pdf_generator.generate_workforce_pdf(data, target_path)  # type: ignore
                elif report_type == ReportType.INCIDENT:
                    self.pdf_generator.generate_incident_pdf(data, target_path)  # type: ignore
                elif report_type == ReportType.CAMERA_COVERAGE:
                    self.pdf_generator.generate_camera_coverage_pdf(data, target_path)  # type: ignore
                elif report_type == ReportType.COMPREHENSIVE_SAFETY:
                    self.pdf_generator.generate_comprehensive_safety_pdf(data, target_path)  # type: ignore

            elif export_format == ReportFormat.EXCEL:
                if report_type == ReportType.WORKFORCE:
                    self.excel_generator.generate_workforce_excel(data, target_path)  # type: ignore
                elif report_type == ReportType.INCIDENT:
                    self.excel_generator.generate_incident_excel(data, target_path)  # type: ignore
                elif report_type == ReportType.CAMERA_COVERAGE:
                    self.excel_generator.generate_camera_coverage_excel(data, target_path)  # type: ignore
                elif report_type == ReportType.COMPREHENSIVE_SAFETY:
                    self.excel_generator.generate_comprehensive_safety_excel(data, target_path)  # type: ignore

            elif export_format == ReportFormat.JSON:
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(data.model_dump(mode="json"), f, indent=2)

            else:
                raise InvalidReportFormatError(f"Unsupported format: {export_format}")

            size_bytes = target_path.stat().st_size if target_path.exists() else 0

            return ReportMetadata(
                report_id=report_id,
                report_type=report_type,
                format=export_format,
                factory_id=factory_id,
                title=f"{report_type.value.replace('_', ' ').title()} Report",
                file_path=str(target_path),
                file_name=filename,
                file_size_bytes=size_bytes,
                mime_type=mime_types.get(export_format, "application/octet-stream"),
                date_from=getattr(data, "date_from", None),
                date_to=getattr(data, "date_to", None),
            )
        except Exception as exc:
            if not isinstance(exc, (InvalidReportFormatError, ReportExportError)):
                raise ReportExportError(f"Export processing failed: {exc}") from exc
            raise
