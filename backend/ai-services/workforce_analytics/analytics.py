"""
workforce_analytics/analytics.py
Public analytics API — the six functions the FastAPI backend will call.

All functions:
  * Accept factory_id (UUID | str) + optional date range.
  * Return validated Pydantic models (JSON-serialisable via .model_dump()).
  * Open their own DB session via get_session() — stateless / thread-safe.
  * Never mutate the database.

DOCUMENTED LIMITATIONS (missing tables in schema):
  - True attendance (clock-in/out): NO shifts/timesheets table → attendance
    is proxied from incident activity.
  - Working hours: NO work_logs/timesheets → not computable.
  - Overtime: NO contracted-hours definition → not computable.
  - Worker↔department assignment: users link to factory only; cameras/sensors
    carry department_id, not users.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .config import (
    DEFAULT_FACTORY_ID,
    HIGH_PRODUCTIVITY_THRESHOLD,
    LOW_PRODUCTIVITY_THRESHOLD,
    RESOLUTION_RATE_TARGET,
)
from .database import get_session
from .repositories import (
    fetch_active_members_in_period,
    fetch_camera_coverage,
    fetch_daily_activity_trend,
    fetch_incident_by_severity,
    fetch_incident_by_state,
    fetch_incident_by_type,
    fetch_incident_summary,
    fetch_per_worker_productivity,
    fetch_role_distribution,
    fetch_user_counts,
)
from .schemas import (
    AttendanceMetrics,
    CameraCoverage,
    CameraRecord,
    IncidentAnalytics,
    IncidentSeveritySplit,
    IncidentStateSplit,
    IncidentTypeSplit,
    ProductivityMetrics,
    WorkerProductivityRecord,
    WorkerRoleSplit,
    WorkforceOverview,
    WorkforceSummary,
)


def _uuid(factory_id: UUID | str) -> UUID:
    return factory_id if isinstance(factory_id, UUID) else UUID(str(factory_id))


@contextmanager
def _managed_session(session: Optional[Session] = None):
    """
    Context manager yielding either an externally-injected Session
    or creating and managing a local Session from get_session().
    When an external session is provided, commit/rollback/close is delegated
    to the outer lifecycle (e.g., FastAPI dependency).
    """
    if session is not None:
        yield session
    else:
        with get_session() as db:
            yield db


# ===========================================================================
# A. WORKFORCE OVERVIEW
# ===========================================================================

def get_workforce_overview(
    factory_id: UUID | str = DEFAULT_FACTORY_ID,
    session: Optional[Session] = None,
) -> WorkforceOverview:
    """
    Returns total / active / inactive worker counts and role distribution.

    Input:  factory_id (UUID)
    Output: WorkforceOverview (Pydantic model)

    Limitations documented in schema:
      - workers_by_department: NOT AVAILABLE (users not linked to departments)
      - working_hours: NOT AVAILABLE (no shift/timesheet table)
    """
    fid = _uuid(factory_id)
    with _managed_session(session) as db:
        counts = fetch_user_counts(db, fid)
        roles  = fetch_role_distribution(db, fid)

    return WorkforceOverview(
        factory_id       = fid,
        total_users      = counts["total_users"],
        active_workers   = counts["active_workers"],
        inactive_workers = counts["inactive_workers"],
        invited_users    = counts["invited_users"],
        disabled_users   = counts["disabled_users"],
        by_role = WorkerRoleSplit(
            factory_admin     = roles.get("factory_admin", 0),
            factory_manager   = roles.get("factory_manager", 0),
            safety_supervisor = roles.get("safety_supervisor", 0),
        ),
    )


# ===========================================================================
# B. ATTENDANCE METRICS (proxy)
# ===========================================================================

def calculate_attendance_metrics(
    factory_id: UUID | str = DEFAULT_FACTORY_ID,
    start: Optional[datetime] = None,
    end:   Optional[datetime] = None,
    session: Optional[Session] = None,
) -> AttendanceMetrics:
    """
    Proxied attendance — based on incident review/resolve activity.

    Formula:
        activity_rate_pct = members_with_activity / total_members × 100

    Input:
        factory_id: UUID
        start, end: optional datetime range filter (UTC)

    Output: AttendanceMetrics

    ⚠ PROXY METRIC — no clock-in/out table in the schema.
    """
    fid = _uuid(factory_id)
    with _managed_session(session) as db:
        counts  = fetch_user_counts(db, fid)
        active  = fetch_active_members_in_period(db, fid, start, end)
        trend   = fetch_daily_activity_trend(db, fid, start, end)

    total      = counts["total_users"]
    active_set = {str(r["user_id"]) for r in active}
    with_activity = len(active_set)
    no_activity   = max(0, total - with_activity)
    rate = round(with_activity / total * 100, 2) if total else 0.0

    return AttendanceMetrics(
        factory_id            = fid,
        period_start          = start,
        period_end            = end,
        total_members         = total,
        members_with_activity = with_activity,
        members_no_activity   = no_activity,
        activity_rate_pct     = rate,
        daily_activity_trend  = trend,
    )


# ===========================================================================
# C. INCIDENT ANALYTICS
# ===========================================================================

def calculate_incident_analytics(
    factory_id: UUID | str = DEFAULT_FACTORY_ID,
    start: Optional[datetime] = None,
    end:   Optional[datetime] = None,
    session: Optional[Session] = None,
) -> IncidentAnalytics:
    """
    Core incident analytics: counts, resolution rate, response times.

    Formula:
        resolution_rate_pct = resolved_incidents / total_incidents × 100

    Input:  factory_id, optional start/end datetime
    Output: IncidentAnalytics
    """
    fid = _uuid(factory_id)
    with _managed_session(session) as db:
        summary  = fetch_incident_summary(db, fid, start, end)
        by_type  = fetch_incident_by_type(db, fid, start, end)
        by_sev   = fetch_incident_by_severity(db, fid, start, end)
        by_state = fetch_incident_by_state(db, fid, start, end)

    total    = summary["total_incidents"] or 0
    resolved = summary["resolved_incidents"] or 0
    rate     = round(resolved / total * 100, 2) if total else 0.0

    return IncidentAnalytics(
        factory_id           = fid,
        period_start         = start,
        period_end           = end,
        total_incidents      = total,
        resolved_incidents   = resolved,
        open_incidents       = summary["open_incidents"] or 0,
        resolution_rate_pct  = rate,
        target_met           = rate / 100 >= RESOLUTION_RATE_TARGET,
        by_type = IncidentTypeSplit(
            ppe_violation             = by_type.get("ppe_violation", 0),
            restricted_zone_intrusion = by_type.get("restricted_zone_intrusion", 0),
            potential_fatigue         = by_type.get("potential_fatigue", 0),
            fall                      = by_type.get("fall", 0),
            fire                      = by_type.get("fire", 0),
            smoke                     = by_type.get("smoke", 0),
            temperature_anomaly       = by_type.get("temperature_anomaly", 0),
            source_failure            = by_type.get("source_failure", 0),
        ),
        by_severity = IncidentSeveritySplit(
            low      = by_sev.get("low", 0),
            medium   = by_sev.get("medium", 0),
            high     = by_sev.get("high", 0),
            critical = by_sev.get("critical", 0),
        ),
        by_state = IncidentStateSplit(
            detected         = by_state.get("detected", 0),
            classified       = by_state.get("classified", 0),
            recorded         = by_state.get("recorded", 0),
            alert_pending    = by_state.get("alert_pending", 0),
            alert_dispatched = by_state.get("alert_dispatched", 0),
            under_review     = by_state.get("under_review", 0),
            resolved         = by_state.get("resolved", 0),
        ),
        avg_time_to_resolve_hrs = (
            float(summary["avg_resolve_hrs"]) if summary["avg_resolve_hrs"] else None
        ),
        avg_time_to_review_hrs = (
            float(summary["avg_review_hrs"]) if summary["avg_review_hrs"] else None
        ),
    )


# ===========================================================================
# D. PRODUCTIVITY METRICS
# ===========================================================================

def calculate_productivity_metrics(
    factory_id: UUID | str = DEFAULT_FACTORY_ID,
    start: Optional[datetime] = None,
    end:   Optional[datetime] = None,
    low_threshold:  int = LOW_PRODUCTIVITY_THRESHOLD,
    high_threshold: int = HIGH_PRODUCTIVITY_THRESHOLD,
    session: Optional[Session] = None,
) -> ProductivityMetrics:
    """
    Per-worker productivity: incidents reviewed + resolved + response times.

    Formula:
        total_handled      = incidents_reviewed + incidents_resolved
        avg_per_worker     = sum(total_handled) / workers_analysed
        productivity_label:
            total_handled <= low_threshold  → "low"
            total_handled >= high_threshold → "high"
            otherwise                       → "normal"

    Input:  factory_id, optional date range, configurable thresholds
    Output: ProductivityMetrics

    ⚠ PROXY METRIC — based on incident handling, not direct performance data.
    """
    fid = _uuid(factory_id)
    with _managed_session(session) as db:
        rows = fetch_per_worker_productivity(db, fid, start, end)

    per_worker: list[WorkerProductivityRecord] = []
    total_handled_all = 0

    for r in rows:
        reviewed = r["incidents_reviewed"]
        resolved = r["incidents_resolved"]
        handled  = reviewed + resolved
        total_handled_all += handled

        if handled <= low_threshold:
            label = "low"
        elif handled >= high_threshold:
            label = "high"
        else:
            label = "normal"

        per_worker.append(WorkerProductivityRecord(
            user_id              = r["user_id"],
            full_name            = r["full_name"],
            role                 = r["role_code"],
            incidents_reviewed   = reviewed,
            incidents_resolved   = resolved,
            total_handled        = handled,
            avg_review_time_hrs  = (float(r["avg_review_hrs"])  if r["avg_review_hrs"]  else None),
            avg_resolve_time_hrs = (float(r["avg_resolve_hrs"]) if r["avg_resolve_hrs"] else None),
            productivity_label   = label,
        ))

    n = len(per_worker)
    avg = round(total_handled_all / n, 2) if n else 0.0

    return ProductivityMetrics(
        factory_id              = fid,
        period_start            = start,
        period_end              = end,
        total_incidents_handled = total_handled_all,
        workers_analysed        = n,
        avg_handled_per_worker  = avg,
        per_worker              = per_worker,
        low_performers  = [w.full_name for w in per_worker if w.productivity_label == "low"],
        high_performers = [w.full_name for w in per_worker if w.productivity_label == "high"],
        thresholds_used = {"low": low_threshold, "high": high_threshold},
    )


# ===========================================================================
# E. CAMERA COVERAGE
# ===========================================================================

def calculate_camera_coverage(
    factory_id:   UUID | str = DEFAULT_FACTORY_ID,
    period_hours: float = 720.0,          # default = 30 days
    session: Optional[Session] = None,
) -> CameraCoverage:
    """
    Camera uptime analytics using unobserved_gaps.

    Formula (per camera):
        coverage_pct = max(0, 1 − total_downtime_hrs / period_hours) × 100

    Overall coverage = average of active camera coverages.

    Input:  factory_id, period_hours (observation window for coverage %)
    Output: CameraCoverage
    """
    fid = _uuid(factory_id)
    with _managed_session(session) as db:
        rows = fetch_camera_coverage(db, fid, period_hours)

    cameras: list[CameraRecord] = []
    active_coverages: list[float] = []

    for r in rows:
        downtime = float(r["total_downtime_hrs"])
        is_active = r["is_active"]
        if is_active and period_hours > 0:
            cov = max(0.0, (1 - downtime / period_hours) * 100)
            active_coverages.append(cov)
        cameras.append(CameraRecord(
            camera_id       = r["camera_id"],
            camera_name     = r["camera_name"],
            department_name = r["department_name"],
            is_active       = is_active,
            total_downtime_hrs = downtime,
            gap_count       = r["gap_count"],
        ))

    overall = round(sum(active_coverages) / len(active_coverages), 2) if active_coverages else 0.0
    total_down = round(sum(c.total_downtime_hrs for c in cameras), 2)

    return CameraCoverage(
        factory_id           = fid,
        period_hours         = period_hours,
        total_cameras        = len(cameras),
        active_cameras       = sum(1 for c in cameras if c.is_active),
        inactive_cameras     = sum(1 for c in cameras if not c.is_active),
        total_downtime_hrs   = total_down,
        overall_coverage_pct = overall,
        per_camera           = cameras,
    )


# ===========================================================================
# F. COMBINED WORKFORCE SUMMARY
# ===========================================================================

def generate_workforce_summary(
    factory_id: UUID | str = DEFAULT_FACTORY_ID,
    start: Optional[datetime] = None,
    end:   Optional[datetime] = None,
    period_hours: float = 720.0,
    session: Optional[Session] = None,
) -> WorkforceSummary:
    """
    Combines all analytics modules into a single structured summary.
    Suitable as the main Operix dashboard payload.

    Input:  factory_id, optional date range, camera period window
    Output: WorkforceSummary (all sub-models included)
    """
    return WorkforceSummary(
        generated_at    = datetime.now(tz=timezone.utc),
        overview        = get_workforce_overview(factory_id, session=session),
        attendance      = calculate_attendance_metrics(factory_id, start, end, session=session),
        incidents       = calculate_incident_analytics(factory_id, start, end, session=session),
        productivity    = calculate_productivity_metrics(factory_id, start, end, session=session),
        camera_coverage = calculate_camera_coverage(factory_id, period_hours, session=session),
    )
