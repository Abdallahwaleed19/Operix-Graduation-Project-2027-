"""
ingestion/database_loader.py
Extracts verified operational data from PostgreSQL (operix_db) in strictly read-only mode.

Transforms relational rows from safety_rules, incidents, cameras, zones, and downtime gaps
into rich factual text documents ready for semantic chunking and embedding.
"""
from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from ..config.settings import get_settings
from ..schemas.contracts import DocumentSourceType
from .document_loader import RawDocument


class DatabaseKnowledgeLoader:
    """Read-only extractor transforming Operix relational data into knowledge documents."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        url = database_url or get_settings().database_url
        self.engine: Engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )

    def extract_safety_rules(self, factory_id: Optional[UUID] = None) -> List[RawDocument]:
        """Extract safety rules and their enforcement criteria."""
        params: dict[str, Any] = {}
        where_clause = ""
        if factory_id:
            where_clause = "WHERE r.factory_id = :factory_id"
            params["factory_id"] = str(factory_id)

        query = f"""
            SELECT
                r.id,
                r.factory_id,
                r.name,
                r.event_type,
                r.severity,
                r.threshold_value,
                r.notify
            FROM safety_rules r
            {where_clause}
            ORDER BY r.name
        """

        docs: List[RawDocument] = []
        with self.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        for row in rows:
            content = (
                f"Safety Rule: '{row['name']}'\n"
                f"Rule ID: {row['id']}\n"
                f"Target Event: {row['event_type']}\n"
                f"Severity Level: {row['severity']}\n"
                f"Threshold: {row['threshold_value'] or 'Immediate trigger'}\n"
                f"Notification Dispatched: {'Yes' if row['notify'] else 'No'}\n"
                f"Description: Enforces mandatory safety compliance against {row['event_type']} "
                f"with {row['severity']} severity level."
            )
            docs.append(
                RawDocument(
                    content=content,
                    source_id=str(row["id"]),
                    source_title=f"Safety Rule: {row['name']}",
                    source_type=DocumentSourceType.DATABASE_SAFETY_RULE,
                    factory_id=UUID(str(row["factory_id"])) if row["factory_id"] else None,
                )
            )
        return docs

    def extract_monitoring_zones(self, factory_id: Optional[UUID] = None) -> List[RawDocument]:
        """Extract monitoring zones and linked camera locations."""
        params: dict[str, Any] = {}
        where_clause = ""
        if factory_id:
            where_clause = "WHERE z.factory_id = :factory_id"
            params["factory_id"] = str(factory_id)

        query = f"""
            SELECT
                z.id,
                z.factory_id,
                z.name AS zone_name,
                z.zone_type,
                c.name AS camera_name,
                d.name AS department_name
            FROM monitoring_zones z
            LEFT JOIN cameras c ON c.id = z.camera_id
            LEFT JOIN departments d ON d.id = c.department_id
            {where_clause}
            ORDER BY z.name
        """

        docs: List[RawDocument] = []
        with self.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        for row in rows:
            content = (
                f"Monitoring Zone: '{row['zone_name']}'\n"
                f"Zone ID: {row['id']}\n"
                f"Zone Type: {row['zone_type']}\n"
                f"Associated Camera: {row['camera_name'] or 'Not assigned'}\n"
                f"Department: {row['department_name'] or 'General Plant'}\n"
                f"Details: Industrial safety zone designated as '{row['zone_type']}' for continuous AI inspection."
            )
            docs.append(
                RawDocument(
                    content=content,
                    source_id=str(row["id"]),
                    source_title=f"Monitoring Zone: {row['zone_name']}",
                    source_type=DocumentSourceType.DATABASE_ZONE,
                    factory_id=UUID(str(row["factory_id"])) if row["factory_id"] else None,
                )
            )
        return docs

    def extract_incidents(
        self,
        factory_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RawDocument]:
        """Extract safety incidents with status and response metrics."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        where_clause = ""
        if factory_id:
            where_clause = "WHERE i.factory_id = :factory_id"
            params["factory_id"] = str(factory_id)

        query = f"""
            SELECT
                i.id,
                i.factory_id,
                i.incident_type,
                i.severity,
                i.state,
                i.opened_at,
                i.reviewed_at,
                i.resolved_at,
                u_rev.full_name AS reviewed_by_name,
                u_res.full_name AS resolved_by_name
            FROM incidents i
            LEFT JOIN users u_rev ON u_rev.id = i.reviewed_by
            LEFT JOIN users u_res ON u_res.id = i.resolved_by
            {where_clause}
            ORDER BY i.opened_at DESC
            LIMIT :limit OFFSET :offset
        """

        docs: List[RawDocument] = []
        with self.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        for row in rows:
            status_text = "RESOLVED" if row["state"] == "resolved" else f"OPEN ({row['state']})"
            content = (
                f"Incident Record: #{row['id']}\n"
                f"Type: {row['incident_type']}\n"
                f"Severity: {row['severity']}\n"
                f"Current State: {status_text}\n"
                f"Opened At: {row['opened_at']}\n"
                f"Reviewed At: {row['reviewed_at'] or 'Pending review'}\n"
                f"Reviewed By: {row['reviewed_by_name'] or 'N/A'}\n"
                f"Resolved At: {row['resolved_at'] or 'Unresolved'}\n"
                f"Resolved By: {row['resolved_by_name'] or 'N/A'}"
            )
            docs.append(
                RawDocument(
                    content=content,
                    source_id=str(row["id"]),
                    source_title=f"Incident #{str(row['id'])[:8]} ({row['incident_type']})",
                    source_type=DocumentSourceType.DATABASE_INCIDENT,
                    factory_id=UUID(str(row["factory_id"])) if row["factory_id"] else None,
                )
            )
        return docs

    def extract_cameras_and_downtime(self, factory_id: Optional[UUID] = None) -> List[RawDocument]:
        """Extract camera inventory and unobserved downtime gaps."""
        params: dict[str, Any] = {}
        where_clause = ""
        if factory_id:
            where_clause = "WHERE c.factory_id = :factory_id"
            params["factory_id"] = str(factory_id)

        query = f"""
            SELECT
                c.id AS camera_id,
                c.factory_id,
                c.name AS camera_name,
                c.camera_type,
                c.is_active,
                d.name AS department_name,
                COUNT(ug.id) AS gap_count,
                COALESCE(SUM(EXTRACT(EPOCH FROM (COALESCE(ug.ended_at, now()) - ug.started_at))/3600), 0) AS downtime_hrs
            FROM cameras c
            LEFT JOIN departments d ON d.id = c.department_id
            LEFT JOIN unobserved_gaps ug ON ug.camera_id = c.id
            {where_clause}
            GROUP BY c.id, c.factory_id, c.name, c.camera_type, c.is_active, d.name
            ORDER BY c.name
        """

        docs: List[RawDocument] = []
        with self.engine.connect() as conn:
            rows = conn.execute(text(query), params).mappings().all()

        for row in rows:
            content = (
                f"Camera Stream: '{row['camera_name']}'\n"
                f"Camera ID: {row['camera_id']}\n"
                f"Type: {row['camera_type']}\n"
                f"Department: {row['department_name'] or 'General'}\n"
                f"Operational Status: {'ACTIVE' if row['is_active'] else 'INACTIVE / MAINTENANCE'}\n"
                f"Recorded Outage Gaps: {row['gap_count']}\n"
                f"Total Downtime: {float(row['downtime_hrs']):.2f} hours"
            )
            docs.append(
                RawDocument(
                    content=content,
                    source_id=str(row["camera_id"]),
                    source_title=f"Camera Telemetry: {row['camera_name']}",
                    source_type=DocumentSourceType.DATABASE_CAMERA,
                    factory_id=UUID(str(row["factory_id"])) if row["factory_id"] else None,
                )
            )
        return docs

    def extract_all(self, factory_id: Optional[UUID] = None) -> List[RawDocument]:
        """Extract complete operational knowledge set from PostgreSQL."""
        all_docs: List[RawDocument] = []
        all_docs.extend(self.extract_safety_rules(factory_id))
        all_docs.extend(self.extract_monitoring_zones(factory_id))
        all_docs.extend(self.extract_incidents(factory_id, limit=200))
        all_docs.extend(self.extract_cameras_and_downtime(factory_id))
        return all_docs
