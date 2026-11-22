"""
incident_evidence/repositories.py
Data-access layer for the evidence_files table.

RULES:
  - Only SELECT queries except create_record() which does INSERT.
  - Never ALTER, DROP, or TRUNCATE.
  - Uses raw parameterized SQL via SQLAlchemy text() to stay explicit
    about the composite FK join: (factory_id, event_id) → events.(factory_id, id).
  - Never assumes evidence_files.event_id directly identifies an incident;
    always JOINs through events.incident_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .exceptions import EvidenceNotFoundError, EvidenceTransactionError
from .schemas import EvidenceFileRecord, EvidenceKind


def _row_to_record(row) -> EvidenceFileRecord:
    """Convert a SQLAlchemy Row to an EvidenceFileRecord."""
    return EvidenceFileRecord(
        id=row.id,
        factory_id=row.factory_id,
        event_id=row.event_id,
        kind=EvidenceKind(row.kind),
        storage_key=row.storage_key,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        duration_s=float(row.duration_s) if row.duration_s is not None else None,
        captured_at=row.captured_at,
        expires_at=row.expires_at,
        purged_at=row.purged_at,
        created_at=row.created_at,
    )


class EvidenceRepository:
    """
    Repository for evidence_files table operations.

    Accepts a SQLAlchemy Connection (or session-like object with execute()).
    Caller is responsible for transaction management.
    """

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_by_id(self, evidence_id: UUID, factory_id: UUID) -> EvidenceFileRecord:
        """Fetch a single evidence record by its PK and factory scope."""
        sql = text("""
            SELECT id, factory_id, event_id, kind, storage_key, content_type,
                   size_bytes, sha256, duration_s, captured_at, expires_at,
                   purged_at, created_at
            FROM evidence_files
            WHERE id = :evidence_id
              AND factory_id = :factory_id
        """)
        row = self._conn.execute(sql, {
            "evidence_id": str(evidence_id),
            "factory_id": str(factory_id),
        }).fetchone()
        if row is None:
            raise EvidenceNotFoundError(
                f"Evidence {evidence_id} not found in factory {factory_id}."
            )
        return _row_to_record(row)

    def get_by_event_id(
        self,
        event_id: UUID,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
    ) -> List[EvidenceFileRecord]:
        """Fetch all evidence for a specific event."""
        conditions = [
            "factory_id = :factory_id",
            "event_id = :event_id",
        ]
        params: dict = {
            "factory_id": str(factory_id),
            "event_id": str(event_id),
        }
        if kind is not None:
            conditions.append("kind = :kind")
            params["kind"] = kind.value

        where = " AND ".join(conditions)
        sql = text(f"""
            SELECT id, factory_id, event_id, kind, storage_key, content_type,
                   size_bytes, sha256, duration_s, captured_at, expires_at,
                   purged_at, created_at
            FROM evidence_files
            WHERE {where}
            ORDER BY captured_at DESC
        """)
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def get_by_incident_id(
        self,
        incident_id: UUID,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
    ) -> List[EvidenceFileRecord]:
        """
        Fetch all evidence linked to an incident via the verified JOIN chain:
          incidents.id ← events.incident_id (nullable)
          events.id ← evidence_files.event_id (composite FK: factory_id + event_id)

        SQL:
          SELECT ef.*
          FROM evidence_files ef
          JOIN events e ON (ef.factory_id = e.factory_id AND ef.event_id = e.id)
          WHERE e.incident_id = :incident_id
            AND ef.factory_id = :factory_id
            [AND ef.kind = :kind]
        """
        conditions = [
            "e.incident_id = :incident_id",
            "ef.factory_id = :factory_id",
        ]
        params: dict = {
            "incident_id": str(incident_id),
            "factory_id": str(factory_id),
        }
        if kind is not None:
            conditions.append("ef.kind = :kind")
            params["kind"] = kind.value

        where = " AND ".join(conditions)
        sql = text(f"""
            SELECT ef.id, ef.factory_id, ef.event_id, ef.kind, ef.storage_key,
                   ef.content_type, ef.size_bytes, ef.sha256, ef.duration_s,
                   ef.captured_at, ef.expires_at, ef.purged_at, ef.created_at
            FROM evidence_files ef
            JOIN events e
              ON ef.factory_id = e.factory_id
             AND ef.event_id = e.id
            WHERE {where}
            ORDER BY ef.captured_at DESC
        """)
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def list_by_factory(
        self,
        factory_id: UUID,
        kind: Optional[EvidenceKind] = None,
        captured_after: Optional[datetime] = None,
        captured_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[EvidenceFileRecord], int]:
        """
        Return a paginated list of evidence for a factory.

        Returns (records, total_count).
        """
        conditions = ["factory_id = :factory_id"]
        params: dict = {"factory_id": str(factory_id)}

        if kind is not None:
            conditions.append("kind = :kind")
            params["kind"] = kind.value
        if captured_after is not None:
            conditions.append("captured_at >= :captured_after")
            params["captured_after"] = captured_after
        if captured_before is not None:
            conditions.append("captured_at <= :captured_before")
            params["captured_before"] = captured_before

        where = " AND ".join(conditions)
        offset = (page - 1) * page_size

        count_sql = text(f"SELECT COUNT(*) FROM evidence_files WHERE {where}")
        total: int = self._conn.execute(count_sql, params).scalar() or 0

        data_sql = text(f"""
            SELECT id, factory_id, event_id, kind, storage_key, content_type,
                   size_bytes, sha256, duration_s, captured_at, expires_at,
                   purged_at, created_at
            FROM evidence_files
            WHERE {where}
            ORDER BY captured_at DESC
            LIMIT :limit OFFSET :offset
        """)
        params["limit"] = page_size
        params["offset"] = offset
        rows = self._conn.execute(data_sql, params).fetchall()
        return [_row_to_record(r) for r in rows], total

    # ------------------------------------------------------------------
    # WRITE  (only create_record and mark_as_purged)
    # ------------------------------------------------------------------

    def create_record(
        self,
        factory_id: UUID,
        event_id: UUID,
        kind: EvidenceKind,
        storage_key: str,
        content_type: str,
        size_bytes: int,
        captured_at: datetime,
        sha256: Optional[str] = None,
        duration_s: Optional[float] = None,
        expires_at: Optional[datetime] = None,
    ) -> EvidenceFileRecord:
        """
        INSERT a new evidence_files row and return the created record.

        Raises EvidenceTransactionError on DB failure.
        """
        new_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)
        sql = text("""
            INSERT INTO evidence_files
              (id, factory_id, event_id, kind, storage_key, content_type,
               size_bytes, sha256, duration_s, captured_at, expires_at, created_at)
            VALUES
              (:id, :factory_id, :event_id, :kind, :storage_key, :content_type,
               :size_bytes, :sha256, :duration_s, :captured_at, :expires_at, :created_at)
            RETURNING id, factory_id, event_id, kind, storage_key, content_type,
                      size_bytes, sha256, duration_s, captured_at, expires_at,
                      purged_at, created_at
        """)
        try:
            row = self._conn.execute(sql, {
                "id": str(new_id),
                "factory_id": str(factory_id),
                "event_id": str(event_id),
                "kind": kind.value,
                "storage_key": storage_key,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "duration_s": duration_s,
                "captured_at": captured_at,
                "expires_at": expires_at,
                "created_at": now,
            }).fetchone()
        except Exception as exc:
            raise EvidenceTransactionError(f"Failed to insert evidence record: {exc}") from exc

        if row is None:
            raise EvidenceTransactionError("INSERT RETURNING returned no row.")
        return _row_to_record(row)

    def mark_as_purged(self, evidence_id: UUID, factory_id: UUID) -> None:
        """Set purged_at to now for the given evidence record."""
        sql = text("""
            UPDATE evidence_files
            SET purged_at = :now
            WHERE id = :evidence_id AND factory_id = :factory_id
        """)
        try:
            self._conn.execute(sql, {
                "now": datetime.now(tz=timezone.utc),
                "evidence_id": str(evidence_id),
                "factory_id": str(factory_id),
            })
        except Exception as exc:
            raise EvidenceTransactionError(f"Failed to mark evidence as purged: {exc}") from exc
