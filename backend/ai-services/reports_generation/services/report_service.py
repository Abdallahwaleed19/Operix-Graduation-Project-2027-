"""
reports_generation/services/report_service.py
High-level report generation facade for Operix Industrial Safety Platform.
Orchestrates data extraction, validation, rendering, and artifact delivery.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..config import DEFAULT_FACTORY_ID, DEFAULT_REPORT_FORMAT, get_reports_storage_dir
from ..exceptions import (
    InvalidReportFormatError,
    InvalidReportTypeError,
    ReportNotFoundError,
)
from ..schemas import ReportFormat, ReportMetadata, ReportType
from .report_data_service import ReportDataService
from .report_export_service import ReportExportService

logger = logging.getLogger("ReportService")


class ReportService:
    """
    Production-grade report orchestrator.
    Can be used standalone, in background workers, or via FastAPI routers.
    """

    def __init__(
        self,
        data_service: Optional[ReportDataService] = None,
        export_service: Optional[ReportExportService] = None,
        storage_dir: Optional[Path] = None,
        engine: Optional[sa.Engine] = None,
        session: Optional[Session] = None,
    ) -> None:
        self.data_service = data_service or ReportDataService(engine=engine, session=session)
        self.export_service = export_service or ReportExportService(storage_dir=storage_dir)
        self.storage_dir = (storage_dir or get_reports_storage_dir()).resolve()
        self._registry: Dict[str, ReportMetadata] = {}

    def generate_report(
        self,
        report_type: ReportType | str,
        format: ReportFormat | str = DEFAULT_REPORT_FORMAT,
        factory_id: Optional[UUID | str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> ReportMetadata:
        """
        Validate parameters, fetch domain data, render artifact, and return metadata.
        """
        # 1. Normalize and validate report type
        if isinstance(report_type, str):
            try:
                report_type = ReportType(report_type.lower())
            except ValueError:
                raise InvalidReportTypeError(
                    f"Invalid report type '{report_type}'. Allowed: {[t.value for t in ReportType]}"
                )

        # 2. Normalize and validate format
        if isinstance(format, str):
            try:
                format = ReportFormat(format.lower())
            except ValueError:
                raise InvalidReportFormatError(
                    f"Invalid format '{format}'. Allowed: {[f.value for f in ReportFormat]}"
                )

        # 3. Resolve factory ID
        fid: UUID = (
            UUID(str(factory_id))
            if factory_id is not None
            else UUID(str(DEFAULT_FACTORY_ID))
        )

        logger.info(f"Generating {report_type.value} ({format.value}) for factory {fid}...")

        # 4. Fetch structured domain data
        if report_type == ReportType.WORKFORCE:
            data = self.data_service.get_workforce_report_data(
                factory_id=fid, date_from=date_from, date_to=date_to
            )
        elif report_type == ReportType.INCIDENT:
            data = self.data_service.get_incident_report_data(
                factory_id=fid, date_from=date_from, date_to=date_to
            )
        elif report_type == ReportType.CAMERA_COVERAGE:
            data = self.data_service.get_camera_coverage_report_data(factory_id=fid)
        elif report_type == ReportType.COMPREHENSIVE_SAFETY:
            data = self.data_service.get_comprehensive_safety_report_data(
                factory_id=fid, date_from=date_from, date_to=date_to
            )
        else:
            raise InvalidReportTypeError(f"Unhandled report type: {report_type}")

        # 5. Render & Export artifact
        metadata = self.export_service.export(
            report_type=report_type,
            export_format=format,
            data=data,
            factory_id=fid,
        )

        # 6. Store in transient registry for runtime retrieval
        self._registry[metadata.report_id] = metadata
        logger.info(f"Report generated successfully: {metadata.report_id} ({metadata.file_size_bytes} bytes)")
        return metadata

    @staticmethod
    def _validate_report_id(report_id: str) -> str:
        if not report_id or "\x00" in report_id or "/" in report_id or "\\" in report_id or ".." in report_id:
            raise ReportNotFoundError(f"Invalid report identifier '{report_id}'.")
        return report_id

    def _safe_contain_path(self, candidate: Path, factory_id: Optional[UUID] = None) -> Path:
        resolved = candidate.resolve()
        base = (self.storage_dir / str(factory_id)).resolve() if factory_id else self.storage_dir.resolve()
        if not resolved.is_relative_to(base):
            raise ReportNotFoundError("Report path escapes authorized storage boundary.")
        return resolved

    def get_report(self, report_id: str, factory_id: UUID) -> ReportMetadata:
        """Lookup report metadata by ID with strict factory isolation.

        Args:
            report_id: The unique report identifier.
            factory_id: Required — the authenticated tenant factory UUID.
                        Raises ValueError if None or falsy.
        """
        if not factory_id:
            raise ValueError("factory_id is required and cannot be None or empty.")
        self._validate_report_id(report_id)
        if report_id in self._registry:
            meta = self._registry[report_id]
            if meta.factory_id != factory_id:
                raise ReportNotFoundError(f"Report '{report_id}' not found.")
            return meta

        search_dirs = [self.storage_dir / str(factory_id)]
        for d in search_dirs:
            try:
                owner_fid = UUID(d.name)
            except ValueError:
                continue
            if factory_id is not None and owner_fid != factory_id:
                continue
            for p in d.glob(f"*_{report_id}.*"):
                self._safe_contain_path(p, factory_id=owner_fid)
                ext = p.suffix.lstrip(".").lower()
                try:
                    fmt = ReportFormat(ext)
                except ValueError:
                    fmt = ReportFormat.PDF

                rtype_str = p.name.split("_REP-")[0]
                try:
                    rtype = ReportType(rtype_str)
                except ValueError:
                    rtype = ReportType.COMPREHENSIVE_SAFETY

                meta = ReportMetadata(
                    report_id=report_id,
                    report_type=rtype,
                    format=fmt,
                    factory_id=owner_fid,
                    title=f"{rtype.value.title()} Report",
                    file_path=str(p),
                    file_name=p.name,
                    file_size_bytes=p.stat().st_size,
                    mime_type="application/pdf" if fmt == ReportFormat.PDF else "application/octet-stream",
                )
                self._registry[report_id] = meta
                return meta

        raise ReportNotFoundError(f"Report '{report_id}' not found.")

    def get_report_file_path(self, report_id: str, factory_id: UUID) -> Path:
        """Resolve and verify existence and containment of physical report artifact.

        Args:
            report_id: The unique report identifier.
            factory_id: Required — the authenticated tenant factory UUID.
                        Raises ValueError if None or falsy.
        """
        if not factory_id:
            raise ValueError("factory_id is required and cannot be None or empty.")
        meta = self.get_report(report_id, factory_id=factory_id)
        if not meta.file_path:
            raise ReportNotFoundError(f"Report artifact path for '{report_id}' is empty.")
        p = self._safe_contain_path(Path(meta.file_path), factory_id=meta.factory_id)
        if not p.exists():
            raise ReportNotFoundError(f"Report file on disk '{p}' is missing.")
        return p

    def list_reports(self, factory_id: UUID) -> List[ReportMetadata]:
        """List currently available generated reports strictly scoped to factory_id.

        Args:
            factory_id: Required — the authenticated tenant factory UUID.
                        Returns empty list if None or falsy (fail-closed).
        """
        if not factory_id:
            return []
        return [r for r in self._registry.values() if r.factory_id == factory_id]


# Singleton instance helper
_service_instance: Optional[ReportService] = None


def get_report_service() -> ReportService:
    """Dependency injection provider."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ReportService()
    return _service_instance
