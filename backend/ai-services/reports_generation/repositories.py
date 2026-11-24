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

from .config import DEFAULT_FACTORY_ID
from .schemas import FactoryInfo

logger = logging.getLogger("ReportRepository")


class ReportRepository:
    """Read-only access to factory and operational metadata using injected Session/Engine."""

    def __init__(
        self,
        engine: Optional[sa.Engine] = None,
        session: Optional[Session] = None,
    ) -> None:
        self.engine = engine
        self.session = session

    def _execute_fetchone(self, query: sa.TextClause, params: Dict[str, Any]):
        """Execute a query and return a single materialized row (or None).

        When an Engine is used, the row is fetched inside the connection context
        so the cursor is never accessed after the connection closes.
        """
        if self.session is not None:
            return self.session.execute(query, params).fetchone()
        if self.engine is not None:
            with self.engine.connect() as conn:
                return conn.execute(query, params).fetchone()
        raise RuntimeError(
            "ReportRepository requires an injected SQLAlchemy Session or Engine from the canonical Backend."
        )

    def _execute_fetchall(self, query: sa.TextClause, params: Dict[str, Any]) -> list:
        """Execute a query and return all materialized rows.

        When an Engine is used, all rows are fetched inside the connection context
        so the cursor is never accessed after the connection closes.
        """
        if self.session is not None:
            return self.session.execute(query, params).fetchall()
        if self.engine is not None:
            with self.engine.connect() as conn:
                return conn.execute(query, params).fetchall()
        raise RuntimeError(
            "ReportRepository requires an injected SQLAlchemy Session or Engine from the canonical Backend."
        )

    def _execute_scalar(self, query: sa.TextClause, params: Dict[str, Any]):
        """Execute a query and return a single scalar value.

        When an Engine is used, the scalar is fetched inside the connection context.
        """
        if self.session is not None:
            return self.session.execute(query, params).scalar()
        if self.engine is not None:
            with self.engine.connect() as conn:
                return conn.execute(query, params).scalar()
        raise RuntimeError(
            "ReportRepository requires an injected SQLAlchemy Session or Engine from the canonical Backend."
        )

    def get_factory_info(self, factory_id: UUID) -> FactoryInfo:
        """Fetch factory name, slug, and timezone."""
        query = sa.text(
            "SELECT id, name, slug, timezone FROM factories WHERE id = :factory_id"
        )
        try:
            row = self._execute_fetchone(query, {"factory_id": str(factory_id)})
            if row:
                return FactoryInfo(
                    factory_id=row.id,
                    name=row.name,
                    slug=row.slug,
                    timezone=row.timezone or "UTC",
                )
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(f"Could not fetch factory from DB ({exc}), using default.")

        return FactoryInfo(factory_id=factory_id)

    def get_unobserved_gaps(self, factory_id: UUID) -> List[Dict[str, Any]]:
        """Fetch active unobserved monitoring gaps."""
        query = sa.text("""
            SELECT id, reason, started_at, ended_at
            FROM unobserved_gaps
            WHERE factory_id = :factory_id
            ORDER BY started_at DESC
            LIMIT 20
        """)
        try:
            rows = self._execute_fetchall(query, {"factory_id": str(factory_id)})
            return [
                {
                    "gap_id": str(r.id),
                    "reason": r.reason,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                }
                for r in rows
            ]
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(f"Could not fetch unobserved gaps: {exc}")
            return []

    def get_active_safety_rules_count(self, factory_id: UUID) -> int:
        """Fetch count of active safety rules."""
        query = sa.text("""
            SELECT count(*) FROM safety_rules
            WHERE factory_id = :factory_id AND is_enabled = true
        """)
        try:
            count = self._execute_scalar(query, {"factory_id": str(factory_id)})
            return int(count or 0)
        except RuntimeError:
            raise
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
            rows = self._execute_fetchall(query, {"factory_id": str(factory_id), "limit": limit})
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
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning(f"Could not fetch detailed incidents: {exc}")
            return []
