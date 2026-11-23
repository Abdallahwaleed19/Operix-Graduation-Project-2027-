"""
workforce_analytics/repositories.py
Raw SQL query layer — all SELECT-only queries against the Operix PostgreSQL schema.

Design decisions:
  * Uses SQLAlchemy text() — no ORM mapping needed for analytics.
  * Every function takes a Session + factory_id UUID.
  * Returns plain Python dicts/lists — the analytics layer does the math.
  * Never issues INSERT / UPDATE / DELETE / DDL.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# A. WORKFORCE OVERVIEW QUERIES
# ---------------------------------------------------------------------------

def fetch_user_counts(db: Session, factory_id: UUID) -> dict:
    """
    Total users in factory with status breakdown and active/inactive membership.
    """
    row = db.execute(text("""
        SELECT
            COUNT(*)                                            AS total_users,
            COUNT(*) FILTER (WHERE fm.is_active = true
                              AND u.status = 'active')         AS active_workers,
            COUNT(*) FILTER (WHERE fm.is_active = false
                              OR  u.status <> 'active')        AS inactive_workers,
            COUNT(*) FILTER (WHERE u.status = 'invited')       AS invited_users,
            COUNT(*) FILTER (WHERE u.status = 'disabled')      AS disabled_users
        FROM factory_memberships fm
        JOIN users u ON u.id = fm.user_id
        WHERE fm.factory_id = :factory_id
    """), {"factory_id": str(factory_id)}).mappings().one()
    return dict(row)


def fetch_role_distribution(db: Session, factory_id: UUID) -> dict:
    """Count of active members per role code."""
    rows = db.execute(text("""
        SELECT r.code, COUNT(*) AS cnt
        FROM factory_memberships fm
        JOIN roles r ON r.id = fm.role_id
        WHERE fm.factory_id = :factory_id
          AND fm.is_active = true
        GROUP BY r.code
    """), {"factory_id": str(factory_id)}).mappings().all()
    return {row["code"]: row["cnt"] for row in rows}


# ---------------------------------------------------------------------------
# B. ATTENDANCE PROXY QUERIES
# ---------------------------------------------------------------------------

def fetch_active_members_in_period(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> list[dict]:
    """
    Members who reviewed or resolved at least one incident in the given period.
    Returns list of {user_id, full_name, activity_date}.
    """
    params: dict = {"factory_id": str(factory_id)}
    date_filter_reviewed = ""
    date_filter_resolved = ""
    if start:
        date_filter_reviewed += " AND i.reviewed_at >= :start"
        date_filter_resolved  += " AND i.resolved_at >= :start"
        params["start"] = start
    if end:
        date_filter_reviewed += " AND i.reviewed_at < :end"
        date_filter_resolved  += " AND i.resolved_at < :end"
        params["end"] = end

    rows = db.execute(text(f"""
        SELECT DISTINCT u.id AS user_id, u.full_name,
               DATE(i.reviewed_at) AS activity_date
        FROM incidents i
        JOIN users u ON u.id = i.reviewed_by
        WHERE i.factory_id = :factory_id
          AND i.reviewed_at IS NOT NULL
          {date_filter_reviewed}
        UNION
        SELECT DISTINCT u.id, u.full_name,
               DATE(i.resolved_at)
        FROM incidents i
        JOIN users u ON u.id = i.resolved_by
        WHERE i.factory_id = :factory_id
          AND i.resolved_at IS NOT NULL
          {date_filter_resolved}
        ORDER BY activity_date
    """), params).mappings().all()
    return [dict(r) for r in rows]


def fetch_daily_activity_trend(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> list[dict]:
    """Active user count per day based on incident review/resolve activity."""
    params: dict = {"factory_id": str(factory_id)}
    date_filter = ""
    if start:
        date_filter += " AND activity_date >= :start"
        params["start"] = start.date() if hasattr(start, "date") else start
    if end:
        date_filter += " AND activity_date < :end"
        params["end"] = end.date() if hasattr(end, "date") else end

    rows = db.execute(text(f"""
        WITH daily AS (
            SELECT DATE(reviewed_at) AS activity_date, reviewed_by AS user_id
            FROM incidents
            WHERE factory_id = :factory_id AND reviewed_at IS NOT NULL
            UNION ALL
            SELECT DATE(resolved_at), resolved_by
            FROM incidents
            WHERE factory_id = :factory_id AND resolved_at IS NOT NULL
        )
        SELECT activity_date, COUNT(DISTINCT user_id) AS active_users
        FROM daily
        WHERE activity_date IS NOT NULL {date_filter}
        GROUP BY activity_date
        ORDER BY activity_date
    """), params).mappings().all()
    return [{"date": str(r["activity_date"]), "active_users": r["active_users"]} for r in rows]


# ---------------------------------------------------------------------------
# C. INCIDENT ANALYTICS QUERIES
# ---------------------------------------------------------------------------

def fetch_incident_summary(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> dict:
    """Aggregate incident counts, resolution rate, avg response times."""
    params: dict = {"factory_id": str(factory_id)}
    date_filter = ""
    if start:
        date_filter += " AND opened_at >= :start"
        params["start"] = start
    if end:
        date_filter += " AND opened_at < :end"
        params["end"] = end

    row = db.execute(text(f"""
        SELECT
            COUNT(*)                                                       AS total_incidents,
            COUNT(*) FILTER (WHERE state = 'resolved')                    AS resolved_incidents,
            COUNT(*) FILTER (WHERE state <> 'resolved')                   AS open_incidents,
            ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at  - opened_at))/3600)
                  FILTER (WHERE resolved_at IS NOT NULL), 2)              AS avg_resolve_hrs,
            ROUND(AVG(EXTRACT(EPOCH FROM (reviewed_at  - opened_at))/3600)
                  FILTER (WHERE reviewed_at IS NOT NULL), 2)              AS avg_review_hrs
        FROM incidents
        WHERE factory_id = :factory_id {date_filter}
    """), params).mappings().one()
    return dict(row)


def fetch_incident_by_type(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> dict:
    params: dict = {"factory_id": str(factory_id)}
    date_filter = ""
    if start:
        date_filter += " AND opened_at >= :start"; params["start"] = start
    if end:
        date_filter += " AND opened_at < :end";   params["end"] = end
    rows = db.execute(text(f"""
        SELECT incident_type::text AS itype, COUNT(*) AS cnt
        FROM incidents
        WHERE factory_id = :factory_id {date_filter}
        GROUP BY incident_type
    """), params).mappings().all()
    return {r["itype"]: r["cnt"] for r in rows}


def fetch_incident_by_severity(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> dict:
    params: dict = {"factory_id": str(factory_id)}
    date_filter = ""
    if start:
        date_filter += " AND opened_at >= :start"; params["start"] = start
    if end:
        date_filter += " AND opened_at < :end";   params["end"] = end
    rows = db.execute(text(f"""
        SELECT severity::text AS sev, COUNT(*) AS cnt
        FROM incidents
        WHERE factory_id = :factory_id {date_filter}
        GROUP BY severity
    """), params).mappings().all()
    return {r["sev"]: r["cnt"] for r in rows}


def fetch_incident_by_state(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> dict:
    params: dict = {"factory_id": str(factory_id)}
    date_filter = ""
    if start:
        date_filter += " AND opened_at >= :start"; params["start"] = start
    if end:
        date_filter += " AND opened_at < :end";   params["end"] = end
    rows = db.execute(text(f"""
        SELECT state::text AS st, COUNT(*) AS cnt
        FROM incidents
        WHERE factory_id = :factory_id {date_filter}
        GROUP BY state
    """), params).mappings().all()
    return {r["st"]: r["cnt"] for r in rows}


# ---------------------------------------------------------------------------
# D. PRODUCTIVITY QUERIES
# ---------------------------------------------------------------------------

def fetch_per_worker_productivity(
    db: Session, factory_id: UUID,
    start: Optional[datetime], end: Optional[datetime]
) -> list[dict]:
    """
    Per-member: incidents reviewed + resolved + avg response times.
    Only members with is_active=true in factory_memberships are included.
    """
    params: dict = {"factory_id": str(factory_id)}
    date_filter_rev = ""
    date_filter_res = ""
    if start:
        date_filter_rev += " AND i.reviewed_at >= :start"
        date_filter_res += " AND i.resolved_at >= :start"
        params["start"] = start
    if end:
        date_filter_rev += " AND i.reviewed_at < :end"
        date_filter_res += " AND i.resolved_at < :end"
        params["end"] = end

    rows = db.execute(text(f"""
        WITH members AS (
            SELECT fm.user_id, u.full_name, r.code AS role_code
            FROM factory_memberships fm
            JOIN users u  ON u.id  = fm.user_id
            JOIN roles r  ON r.id  = fm.role_id
            WHERE fm.factory_id = :factory_id
              AND fm.is_active   = true
        ),
        reviewed AS (
            SELECT
                i.reviewed_by                                                   AS user_id,
                COUNT(*)                                                         AS incidents_reviewed,
                ROUND(AVG(EXTRACT(EPOCH FROM (i.reviewed_at - i.opened_at))/3600), 2)
                                                                                AS avg_review_hrs
            FROM incidents i
            WHERE i.factory_id = :factory_id
              AND i.reviewed_by IS NOT NULL
              AND i.reviewed_at IS NOT NULL
              {date_filter_rev}
            GROUP BY i.reviewed_by
        ),
        resolved AS (
            SELECT
                i.resolved_by                                                   AS user_id,
                COUNT(*)                                                         AS incidents_resolved,
                ROUND(AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.opened_at))/3600), 2)
                                                                                AS avg_resolve_hrs
            FROM incidents i
            WHERE i.factory_id = :factory_id
              AND i.resolved_by IS NOT NULL
              AND i.resolved_at IS NOT NULL
              {date_filter_res}
            GROUP BY i.resolved_by
        )
        SELECT
            m.user_id,
            m.full_name,
            m.role_code,
            COALESCE(rv.incidents_reviewed, 0) AS incidents_reviewed,
            COALESCE(rs.incidents_resolved, 0) AS incidents_resolved,
            rv.avg_review_hrs,
            rs.avg_resolve_hrs
        FROM members m
        LEFT JOIN reviewed rv ON rv.user_id = m.user_id
        LEFT JOIN resolved rs ON rs.user_id = m.user_id
        ORDER BY
            (COALESCE(rv.incidents_reviewed, 0) + COALESCE(rs.incidents_resolved, 0)) DESC,
            m.full_name
    """), params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# E. CAMERA COVERAGE QUERIES
# ---------------------------------------------------------------------------

def fetch_camera_coverage(
    db: Session, factory_id: UUID,
    period_hours: float
) -> list[dict]:
    """Downtime hours per camera from unobserved_gaps."""
    rows = db.execute(text("""
        SELECT
            c.id              AS camera_id,
            c.name            AS camera_name,
            d.name            AS department_name,
            c.is_active,
            COUNT(ug.id)      AS gap_count,
            COALESCE(
                ROUND(SUM(
                    EXTRACT(EPOCH FROM (
                        COALESCE(ug.ended_at, now()) - ug.started_at
                    )) / 3600
                )::numeric, 2),
                0
            )                  AS total_downtime_hrs
        FROM cameras c
        LEFT JOIN departments d        ON d.id = c.department_id
                                      AND d.factory_id = c.factory_id
        LEFT JOIN unobserved_gaps ug   ON ug.camera_id  = c.id
                                      AND ug.factory_id = c.factory_id
        WHERE c.factory_id = :factory_id
        GROUP BY c.id, c.name, d.name, c.is_active
        ORDER BY c.name
    """), {"factory_id": str(factory_id)}).mappings().all()
    return [dict(r) for r in rows]
