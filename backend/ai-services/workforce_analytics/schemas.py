"""
workforce_analytics/schemas.py
Pydantic v2 schemas — structured, JSON-serialisable analytics output.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkerRoleSplit(BaseModel):
    factory_admin: int     = Field(0)
    factory_manager: int   = Field(0)
    safety_supervisor: int = Field(0)


class WorkerProductivityRecord(BaseModel):
    user_id:              UUID
    full_name:            str
    role:                 str
    incidents_reviewed:   int
    incidents_resolved:   int
    total_handled:        int
    avg_review_time_hrs:  Optional[float] = None
    avg_resolve_time_hrs: Optional[float] = None
    productivity_label:   str


class IncidentTypeSplit(BaseModel):
    ppe_violation:             int = 0
    restricted_zone_intrusion: int = 0
    potential_fatigue:         int = 0
    fall:                      int = 0
    fire:                      int = 0
    smoke:                     int = 0
    temperature_anomaly:       int = 0
    source_failure:            int = 0


class IncidentSeveritySplit(BaseModel):
    low:      int = 0
    medium:   int = 0
    high:     int = 0
    critical: int = 0


class IncidentStateSplit(BaseModel):
    detected:         int = 0
    classified:       int = 0
    recorded:         int = 0
    alert_pending:    int = 0
    alert_dispatched: int = 0
    under_review:     int = 0
    resolved:         int = 0


class CameraRecord(BaseModel):
    camera_id:          UUID
    camera_name:        str
    department_name:    Optional[str] = None
    is_active:          bool
    total_downtime_hrs: float
    gap_count:          int


class WorkforceOverview(BaseModel):
    factory_id:       UUID
    total_users:      int
    active_workers:   int
    inactive_workers: int
    invited_users:    int
    disabled_users:   int
    by_role:          WorkerRoleSplit
    workers_by_department: str = Field(
        default="NOT AVAILABLE — users are linked to factory, not department. "
                "Only cameras/sensors carry a department_id in this schema."
    )
    working_hours: str = Field(
        default="NOT AVAILABLE — no shifts/timesheets/clock-in-out table in schema."
    )


class AttendanceMetrics(BaseModel):
    factory_id:            UUID
    period_start:          Optional[datetime] = None
    period_end:            Optional[datetime] = None
    total_members:         int
    members_with_activity: int
    members_no_activity:   int
    activity_rate_pct:     float
    daily_activity_trend:  list[dict] = Field(default_factory=list)
    data_quality_note: str = Field(
        default="PROXY METRIC — based on incident review/resolve activity. "
                "No clock-in/out table exists in this schema."
    )


class IncidentAnalytics(BaseModel):
    factory_id:              UUID
    period_start:            Optional[datetime] = None
    period_end:              Optional[datetime] = None
    total_incidents:         int
    resolved_incidents:      int
    open_incidents:          int
    resolution_rate_pct:     float
    target_met:              bool
    by_type:                 IncidentTypeSplit
    by_severity:             IncidentSeveritySplit
    by_state:                IncidentStateSplit
    avg_time_to_resolve_hrs: Optional[float] = None
    avg_time_to_review_hrs:  Optional[float] = None


class ProductivityMetrics(BaseModel):
    factory_id:               UUID
    period_start:             Optional[datetime] = None
    period_end:               Optional[datetime] = None
    total_incidents_handled:  int
    workers_analysed:         int
    avg_handled_per_worker:   float
    per_worker:               list[WorkerProductivityRecord]
    low_performers:           list[str]
    high_performers:          list[str]
    thresholds_used:          dict
    data_quality_note: str = Field(
        default="PROXY METRIC — productivity is incident review/resolve count. "
                "No task table or direct performance measurement exists."
    )


class CameraCoverage(BaseModel):
    factory_id:           UUID
    period_hours:         float
    total_cameras:        int
    active_cameras:       int
    inactive_cameras:     int
    total_downtime_hrs:   float
    overall_coverage_pct: float
    per_camera:           list[CameraRecord]


class WorkforceSummary(BaseModel):
    generated_at:    datetime
    overview:        WorkforceOverview
    attendance:      AttendanceMetrics
    incidents:       IncidentAnalytics
    productivity:    ProductivityMetrics
    camera_coverage: CameraCoverage
