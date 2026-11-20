"""
workforce_analytics/services/analytics_service.py
Service layer wrapping existing Workforce Analytics algorithms.

Design Principles:
  - Clean separation: Acts as an orchestrator/facade between API routers and core analytics.
  - No duplicated calculation: Directly reuses functions from workforce_analytics.analytics.
  - Safe session management: Analytics algorithms manage their own scoped DB sessions.
  - Stateless & thread-safe: No global state or persistent DB connection held by the service.
  - Ready for FastAPI: Can be instantiated directly or injected via FastAPI Depends().
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from ..analytics import (
    calculate_attendance_metrics,
    calculate_camera_coverage,
    calculate_incident_analytics,
    calculate_productivity_metrics,
    generate_workforce_summary,
    get_workforce_overview,
)
from ..config import (
    DEFAULT_FACTORY_ID,
    HIGH_PRODUCTIVITY_THRESHOLD,
    LOW_PRODUCTIVITY_THRESHOLD,
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


class WorkforceAnalyticsService:
    """
    Independent service facade for Workforce Analytics operations.
    Exposes typed methods returning validated Pydantic models or JSON-compatible dicts.
    """

    def __init__(self, default_factory_id: Optional[UUID | str] = None) -> None:
        self.default_factory_id = (
            UUID(str(default_factory_id))
            if default_factory_id is not None
            else UUID(str(DEFAULT_FACTORY_ID))
        )

    def _resolve_factory_id(self, factory_id: Optional[UUID | str]) -> UUID:
        """Resolve provided factory_id or fallback to configured default."""
        if factory_id is not None:
            return factory_id if isinstance(factory_id, UUID) else UUID(str(factory_id))
        return self.default_factory_id

    def check_health(self) -> dict[str, Any]:
        """Verify database connectivity."""
        healthy = test_connection()
        return {
            "status": "healthy" if healthy else "unhealthy",
            "database_connected": healthy,
            "default_factory_id": str(self.default_factory_id),
        }

    # -----------------------------------------------------------------------
    # 1. Workforce Overview
    # -----------------------------------------------------------------------
    def get_workforce_overview(
        self,
        factory_id: Optional[UUID | str] = None,
        *,
        as_dict: bool = False,
    ) -> WorkforceOverview | dict[str, Any]:
        """
        Retrieve overall workforce metrics: total workers, active/inactive split,
        and role breakdown.
        """
        fid = self._resolve_factory_id(factory_id)
        result = get_workforce_overview(factory_id=fid)
        return result.model_dump(mode="json") if as_dict else result

    # -----------------------------------------------------------------------
    # 2. Attendance Analytics (Proxy)
    # -----------------------------------------------------------------------
    def get_attendance_metrics(
        self,
        factory_id: Optional[UUID | str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        *,
        as_dict: bool = False,
    ) -> AttendanceMetrics | dict[str, Any]:
        """
        Retrieve attendance metrics based on incident review/resolve activity.
        Supports date filtering over start_date and end_date.
        """
        fid = self._resolve_factory_id(factory_id)
        result = calculate_attendance_metrics(
            factory_id=fid,
            start=start_date,
            end=end_date,
        )
        return result.model_dump(mode="json") if as_dict else result

    # -----------------------------------------------------------------------
    # 3. Incident Analytics
    # -----------------------------------------------------------------------
    def get_incident_analytics(
        self,
        factory_id: Optional[UUID | str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        *,
        as_dict: bool = False,
    ) -> IncidentAnalytics | dict[str, Any]:
        """
        Retrieve safety incident counts, resolution rates, response times,
        and severity/state/type distributions.
        Supports date filtering over start_date and end_date.
        """
        fid = self._resolve_factory_id(factory_id)
        result = calculate_incident_analytics(
            factory_id=fid,
            start=start_date,
            end=end_date,
        )
        return result.model_dump(mode="json") if as_dict else result

    # -----------------------------------------------------------------------
    # 4. Productivity Metrics (Proxy)
    # -----------------------------------------------------------------------
    def get_productivity_metrics(
        self,
        factory_id: Optional[UUID | str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        low_threshold: Optional[int] = None,
        high_threshold: Optional[int] = None,
        *,
        as_dict: bool = False,
    ) -> ProductivityMetrics | dict[str, Any]:
        """
        Retrieve per-worker productivity based on reviewed and resolved incidents.
        Identifies high and low performers using configurable thresholds.
        """
        fid = self._resolve_factory_id(factory_id)
        low = low_threshold if low_threshold is not None else LOW_PRODUCTIVITY_THRESHOLD
        high = high_threshold if high_threshold is not None else HIGH_PRODUCTIVITY_THRESHOLD

        result = calculate_productivity_metrics(
            factory_id=fid,
            start=start_date,
            end=end_date,
            low_threshold=low,
            high_threshold=high,
        )
        return result.model_dump(mode="json") if as_dict else result

    # -----------------------------------------------------------------------
    # 5. Camera Coverage & Downtime
    # -----------------------------------------------------------------------
    def get_camera_coverage(
        self,
        factory_id: Optional[UUID | str] = None,
        period_hours: float = 720.0,
        *,
        as_dict: bool = False,
    ) -> CameraCoverage | dict[str, Any]:
        """
        Retrieve camera uptime and coverage percentages based on unobserved gaps.
        """
        fid = self._resolve_factory_id(factory_id)
        result = calculate_camera_coverage(
            factory_id=fid,
            period_hours=period_hours,
        )
        return result.model_dump(mode="json") if as_dict else result

    # -----------------------------------------------------------------------
    # 6. Unified Workforce Summary
    # -----------------------------------------------------------------------
    def get_workforce_summary(
        self,
        factory_id: Optional[UUID | str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period_hours: float = 720.0,
        *,
        as_dict: bool = False,
    ) -> WorkforceSummary | dict[str, Any]:
        """
        Consolidate all workforce analytics metrics into a single structured report.
        Ideal for main dashboard overview cards.
        """
        fid = self._resolve_factory_id(factory_id)
        result = generate_workforce_summary(
            factory_id=fid,
            start=start_date,
            end=end_date,
            period_hours=period_hours,
        )
        return result.model_dump(mode="json") if as_dict else result
