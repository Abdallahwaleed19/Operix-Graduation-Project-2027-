"""
reports_generation/services/report_data_service.py
Data assembly and normalization service for reports.
Reuses WorkforceAnalyticsService to guarantee zero calculation duplication.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from workforce_analytics.services.analytics_service import WorkforceAnalyticsService

from ..exceptions import InvalidDateRangeError, ReportDataExtractionError
from ..repositories import ReportRepository
from ..schemas import (
    CameraCoverageReportData,
    ComprehensiveSafetyReportData,
    IncidentReportData,
    WorkforceReportData,
)


class ReportDataService:
    """
    Coordinates data retrieval for all report types by orchestrating
    WorkforceAnalyticsService and ReportRepository.
    """

    def __init__(
        self,
        analytics_service: Optional[WorkforceAnalyticsService] = None,
        repository: Optional[ReportRepository] = None,
        engine: Optional[sa.Engine] = None,
        session: Optional[Session] = None,
    ) -> None:
        self.session = session
        self.analytics_service = analytics_service or WorkforceAnalyticsService(session=session)
        self.repository = repository or ReportRepository(engine=engine)

    def _validate_date_range(self, date_from: Optional[date], date_to: Optional[date]) -> None:
        """Ensure date_from is not after date_to."""
        if date_from and date_to and date_from > date_to:
            raise InvalidDateRangeError(
                f"Invalid date range: start date ({date_from}) cannot be after end date ({date_to})."
            )

    def get_workforce_report_data(
        self,
        factory_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> WorkforceReportData:
        """Assemble complete data package for Workforce Report."""
        self._validate_date_range(date_from, date_to)
        now = datetime.now(tz=timezone.utc)
        factory_info = self.repository.get_factory_info(factory_id)

        try:
            overview = self.analytics_service.get_workforce_overview(factory_id=factory_id).model_dump()
            attendance = self.analytics_service.get_attendance_metrics(
                factory_id=factory_id, start_date=date_from, end_date=date_to
            ).model_dump()
            productivity = self.analytics_service.get_productivity_metrics(factory_id=factory_id).model_dump()
            incident_analytics = self.analytics_service.get_incident_analytics(
                factory_id=factory_id, start_date=date_from, end_date=date_to
            ).model_dump()

            return WorkforceReportData(
                factory_info=factory_info,
                generated_at=now,
                date_from=date_from,
                date_to=date_to,
                overview=overview,
                attendance_proxy=attendance,
                productivity_proxy=productivity,
                incident_workforce={
                    "total_incidents": incident_analytics.get("total_incidents", 0),
                    "resolution_rate": incident_analytics.get("resolution_rate", 0.0),
                },
            )
        except Exception as exc:
            raise ReportDataExtractionError(f"Failed to gather workforce report data: {exc}") from exc

    def get_incident_report_data(
        self,
        factory_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> IncidentReportData:
        """Assemble data package for Incident Report."""
        self._validate_date_range(date_from, date_to)
        now = datetime.now(tz=timezone.utc)
        factory_info = self.repository.get_factory_info(factory_id)

        try:
            incidents = self.analytics_service.get_incident_analytics(
                factory_id=factory_id, start_date=date_from, end_date=date_to
            ).model_dump()
            detailed_list = self.repository.get_detailed_incidents(factory_id=factory_id)

            return IncidentReportData(
                factory_info=factory_info,
                generated_at=now,
                date_from=date_from,
                date_to=date_to,
                total_incidents=incidents.get("total_incidents", 0),
                severity_breakdown=incidents.get("severity_breakdown", {}),
                state_breakdown=incidents.get("state_breakdown", {}),
                resolution_rate=incidents.get("resolution_rate", 0.0),
                avg_resolution_time_minutes=incidents.get("avg_resolution_time_minutes", 0.0),
                incidents_list=detailed_list,
            )
        except Exception as exc:
            raise ReportDataExtractionError(f"Failed to gather incident report data: {exc}") from exc

    def get_camera_coverage_report_data(
        self,
        factory_id: UUID,
    ) -> CameraCoverageReportData:
        """Assemble data package for Camera Coverage Report."""
        now = datetime.now(tz=timezone.utc)
        factory_info = self.repository.get_factory_info(factory_id)

        try:
            coverage = self.analytics_service.get_camera_coverage(factory_id=factory_id).model_dump()
            gaps = self.repository.get_unobserved_gaps(factory_id=factory_id)

            return CameraCoverageReportData(
                factory_info=factory_info,
                generated_at=now,
                total_cameras=coverage.get("total_cameras", 0),
                active_cameras=coverage.get("active_cameras", 0),
                coverage_percentage=coverage.get("coverage_percentage", 0.0),
                per_camera_status=coverage.get("per_camera_status", []),
                unobserved_gaps=gaps,
            )
        except Exception as exc:
            raise ReportDataExtractionError(f"Failed to gather camera coverage report data: {exc}") from exc

    def get_comprehensive_safety_report_data(
        self,
        factory_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> ComprehensiveSafetyReportData:
        """Synthesize unified factory safety assessment."""
        self._validate_date_range(date_from, date_to)
        now = datetime.now(tz=timezone.utc)
        factory_info = self.repository.get_factory_info(factory_id)

        try:
            summary = self.analytics_service.get_workforce_summary(
                factory_id=factory_id, start_date=date_from, end_date=date_to
            ).model_dump()
            rules_count = self.repository.get_active_safety_rules_count(factory_id=factory_id)

            # Composite Safety Health Score calculation:
            # Deterministically derived from verifiable monitoring and resolution telemetry:
            #   - 60% Camera Vision Coverage Ratio (monitoring health across active plant zones)
            #   - 40% Incident Resolution Rate (timely mitigation of identified safety events)
            # Note: Active worker ratio is deliberately excluded from the composite index because
            # factory user accounts in operix_db represent static memberships rather than verified
            # real-time physical badge-ins.
            cov_pct = summary.get("camera_coverage", {}).get("coverage_percentage", 0.0)
            res_rate = summary.get("incidents", {}).get("resolution_rate", 0.0) * 100.0
            health_score = round(min(100.0, max(0.0, (cov_pct * 0.6) + (res_rate * 0.4))), 1)

            return ComprehensiveSafetyReportData(
                factory_info=factory_info,
                generated_at=now,
                date_from=date_from,
                date_to=date_to,
                safety_health_score=health_score,
                workforce_overview=summary.get("workforce", {}),
                incident_analytics=summary.get("incidents", {}),
                camera_coverage=summary.get("camera_coverage", {}),
                active_safety_rules_count=rules_count,
            )
        except Exception as exc:
            raise ReportDataExtractionError(f"Failed to gather comprehensive safety report data: {exc}") from exc
