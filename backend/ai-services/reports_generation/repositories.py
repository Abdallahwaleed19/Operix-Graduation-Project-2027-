"""
reports_generation/repositories.py
Read-only repository layer for additional report contextual data.
Reuses the database connection safely.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from .config import DATABASE_URL, DEFAULT_FACTORY_ID
from .schemas import FactoryInfo

logger = logging.getLogger("ReportRepository")


class ReportRepository:
    """Read-only access to factory and operational metadata."""

    def __init__(self, engine: Optional[sa.Engine] = None) -> None:
        if engine:
            self.engine = engine
        else:
            self.engine = sa.create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                echo=False,
            )

    def get_factory_info(self, factory_id: UUID) -> FactoryInfo:
        """Fetch factory name, slug, and timezone."""
        query = sa.text(
            "SELECT id, name, slug, timezone FROM factories WHERE id = :factory_id"
        )
        try:
            with self.engine.connect() as conn:
                row = conn.execute(query, {"factory_id": factory_id}).fetchone()
                if row:
                    return FactoryInfo(
                        factory_id=row.id,
                        name=row.name,
                        slug=row.slug,
                        timezone=row.timezone or "UTC",
                    )
        except Exception as exc:
            logger.warning(f"Could not fetch factory from DB ({exc}), using default.")

        return FactoryInfo(factory_id=factory_id)

    def get_unobserved_gaps(self, factory_id: UUID) -> List[Dict[str, Any]]:
        """Fetch active unobserved monitoring gaps."""
        query = sa.text("""
            SELECT id, reason, severity, started_at, resolved_at
            FROM unobserved_gaps
            WHERE factory_id = :factory_id
            ORDER BY started_at DESC
            LIMIT 20
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query, {"factory_id": factory_id}).fetchall()
                return [
                    {
                        "gap_id": str(r.id),
                        "reason": r.reason,
                        "severity": r.severity,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning(f"Could not fetch unobserved gaps: {exc}")
            return []

    def get_active_safety_rules_count(self, factory_id: UUID) -> int:
        """Fetch count of active safety rules."""
        query = sa.text("""
            SELECT count(*) FROM safety_rules
            WHERE factory_id = :factory_id AND is_active = true
        """)
        try:
            with self.engine.connect() as conn:
                count = conn.execute(query, {"factory_id": factory_id}).scalar()
                return int(count or 0)
        except Exception as exc:
            logger.warning(f"Could not count safety rules: {exc}")
            return 0

    def get_detailed_incidents(
        self, factory_id: UUID, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Fetch incident records for detailed tabular breakdown."""
        query = sa.text("""
            SELECT id, incident_type, severity, state, opened_at, resolved_at, resolution_note
            FROM incidents
            WHERE factory_id = :factory_id
            ORDER BY opened_at DESC
            LIMIT :limit
        """)
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(query, {"factory_id": factory_id, "limit": limit}).fetchall()
                return [
                    {
                        "incident_id": str(r.id)[:8] + "...",
                        "type": r.incident_type,
                        "severity": r.severity,
                        "state": r.state,
                        "opened_at": r.opened_at.strftime("%Y-%m-%d %H:%M") if r.opened_at else "-",
                        "resolved_at": r.resolved_at.strftime("%Y-%m-%d %H:%M") if r.resolved_at else "-",
                    }
                    for r in rows
                ]
        except Exception as exc:
            logger.warning(f"Could not fetch detailed incidents: {exc}")
            return []
