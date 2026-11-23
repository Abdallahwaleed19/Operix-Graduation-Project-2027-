"""
reports_generation/schemas.py
Pydantic v2 data models and enums for report generation.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Supported report categories."""
    WORKFORCE = "workforce"
    INCIDENT = "incident"
    CAMERA_COVERAGE = "camera_coverage"
    COMPREHENSIVE_SAFETY = "comprehensive_safety"


class ReportFormat(str, Enum):
    """Supported output formats."""
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"


PROXY_METRIC_DISCLAIMER = (
    "DISCLAIMER: Attendance and productivity indicators in this report are proxy metrics "
    "algorithmically estimated from safety incident interaction telemetry and supervisor resolution logs. "
    "They do NOT constitute verified timecard attendance, biometric records, or mechanical output tracking."
)


class ReportMetadata(BaseModel):
    """Metadata describing a generated report."""
    report_id: str = Field(description="Unique report execution identifier (UUID or reference).")
    report_type: ReportType
    format: ReportFormat
    factory_id: UUID
    title: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    file_path: Optional[str] = Field(default=None, description="Absolute or relative file path on disk.")
    file_name: str
    file_size_bytes: int = 0
    mime_type: str
    has_proxy_metrics: bool = True
    disclaimer: str = PROXY_METRIC_DISCLAIMER


class FactoryInfo(BaseModel):
    """Factory descriptive metadata."""
    factory_id: UUID
    name: str = "Operix Industrial Plant"
    slug: str = "operix-plant-01"
    timezone: str = "UTC"


# ---------------------------------------------------------------------------
# Report Structured Data Schemas
# ---------------------------------------------------------------------------

class WorkforceReportData(BaseModel):
    """Structured data payload for Workforce Report."""
    factory_info: FactoryInfo
    generated_at: datetime
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    overview: Dict[str, Any]
    attendance_proxy: Dict[str, Any]
    productivity_proxy: Dict[str, Any]
    incident_workforce: Dict[str, Any]
    disclaimer: str = PROXY_METRIC_DISCLAIMER


class IncidentReportData(BaseModel):
    """Structured data payload for Incident Report."""
    factory_info: FactoryInfo
    generated_at: datetime
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    total_incidents: int
    severity_breakdown: Dict[str, int]
    state_breakdown: Dict[str, int]
    resolution_rate: float
    avg_resolution_time_minutes: float
    incidents_list: List[Dict[str, Any]] = Field(default_factory=list)


class CameraCoverageReportData(BaseModel):
    """Structured data payload for Camera Coverage Report."""
    factory_info: FactoryInfo
    generated_at: datetime
    total_cameras: int
    active_cameras: int
    coverage_percentage: float
    per_camera_status: List[Dict[str, Any]]
    unobserved_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    department_coverage: Dict[str, Any] = Field(default_factory=dict)


class ComprehensiveSafetyReportData(BaseModel):
    """Unified Safety Report synthesizing all operational domains."""
    factory_info: FactoryInfo
    generated_at: datetime
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    safety_health_score: float = Field(ge=0.0, le=100.0, description="Composite plant safety index.")
    workforce_overview: Dict[str, Any]
    incident_analytics: Dict[str, Any]
    camera_coverage: Dict[str, Any]
    active_safety_rules_count: int
    disclaimer: str = PROXY_METRIC_DISCLAIMER
