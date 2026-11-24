"""
app/services/incident_service.py
Business logic for tenant-scoped Incident management and post-commit WebSocket broadcasts.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.errors import OperixException, ResourceNotFoundException
from ..core.websocket import ws_manager
from ..models.enums import EventType, IncidentState, SeverityLevel
from ..models.incidents import Incident
from ..schemas.incidents import IncidentCreate, IncidentUpdate


class IncidentService:
    """Caller owns DB session commit/rollback; service only flushes and stages WS events."""

    @staticmethod
    def list_incidents(
        db: Session,
        factory_id: uuid.UUID,
        state: Optional[IncidentState] = None,
        severity: Optional[SeverityLevel] = None,
        incident_type: Optional[EventType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Incident], int]:
        filters = [Incident.factory_id == factory_id]
        if state is not None:
            filters.append(Incident.state == state)
        if severity is not None:
            filters.append(Incident.severity == severity)
        if incident_type is not None:
            filters.append(Incident.incident_type == incident_type)

        total = db.execute(select(func.count()).select_from(Incident).where(*filters)).scalar_one()
        items = (
            db.execute(
                select(Incident)
                .where(*filters)
                .order_by(Incident.opened_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(items), int(total)

    @staticmethod
    def get_incident(
        db: Session,
        factory_id: uuid.UUID,
        incident_id: uuid.UUID,
    ) -> Incident:
        incident = db.execute(
            select(Incident).where(
                Incident.factory_id == factory_id,
                Incident.id == incident_id,
            )
        ).scalar_one_or_none()
        if incident is None:
            raise ResourceNotFoundException("Incident", incident_id)
        return incident

    @staticmethod
    def create_incident(
        db: Session,
        factory_id: uuid.UUID,
        incident_in: IncidentCreate,
    ) -> Tuple[Incident, Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        incident = Incident(
            factory_id=factory_id,
            incident_type=incident_in.incident_type,
            severity=incident_in.severity,
            state=IncidentState.DETECTED,
            opened_at=now,
            last_event_at=now,
        )
        db.add(incident)
        db.flush()
        db.refresh(incident)
        payload = {
            "type": "incident_created",
            "factory_id": str(factory_id),
            "incident_id": str(incident.id),
            "incident_type": incident.incident_type.value,
            "severity": incident.severity.value,
            "state": incident.state.value,
            "timestamp": now.isoformat(),
        }
        return incident, payload

    @staticmethod
    def acknowledge_incident(
        db: Session,
        factory_id: uuid.UUID,
        user_id: uuid.UUID,
        incident_id: uuid.UUID,
    ) -> Tuple[Incident, Dict[str, Any]]:
        incident = IncidentService.get_incident(db, factory_id, incident_id)
        if incident.state == IncidentState.RESOLVED:
            raise OperixException(
                message="Cannot acknowledge an incident that is already resolved.",
                status_code=400,
                error_code="INVALID_STATE_TRANSITION",
            )
        now = datetime.now(timezone.utc)
        incident.state = IncidentState.UNDER_REVIEW
        incident.reviewed_by = user_id
        incident.reviewed_at = now
        incident.updated_at = now
        db.flush()
        db.refresh(incident)
        payload = {
            "type": "incident_acknowledged",
            "factory_id": str(factory_id),
            "incident_id": str(incident.id),
            "state": incident.state.value,
            "reviewed_by": str(user_id),
            "timestamp": now.isoformat(),
        }
        return incident, payload

    @staticmethod
    def resolve_incident(
        db: Session,
        factory_id: uuid.UUID,
        user_id: uuid.UUID,
        incident_id: uuid.UUID,
        resolution_note: Optional[str] = None,
    ) -> Tuple[Incident, Dict[str, Any]]:
        incident = IncidentService.get_incident(db, factory_id, incident_id)
        if incident.state == IncidentState.RESOLVED:
            raise OperixException(
                message="Incident is already resolved.",
                status_code=400,
                error_code="INVALID_STATE_TRANSITION",
            )
        now = datetime.now(timezone.utc)
        incident.state = IncidentState.RESOLVED
        incident.resolved_by = user_id
        incident.resolved_at = now
        if resolution_note is not None:
            incident.resolution_note = resolution_note
        incident.updated_at = now
        db.flush()
        db.refresh(incident)
        payload = {
            "type": "incident_resolved",
            "factory_id": str(factory_id),
            "incident_id": str(incident.id),
            "state": incident.state.value,
            "resolved_by": str(user_id),
            "timestamp": now.isoformat(),
        }
        return incident, payload

    @staticmethod
    def update_incident(
        db: Session,
        factory_id: uuid.UUID,
        incident_id: uuid.UUID,
        incident_in: IncidentUpdate,
    ) -> Incident:
        incident = IncidentService.get_incident(db, factory_id, incident_id)
        if incident_in.severity is not None:
            incident.severity = incident_in.severity
        if incident_in.resolution_note is not None:
            incident.resolution_note = incident_in.resolution_note
        incident.updated_at = datetime.now(timezone.utc)
        db.flush()
        db.refresh(incident)
        return incident

    @staticmethod
    async def broadcast_event(factory_id: uuid.UUID, payload: Dict[str, Any]) -> None:
        await ws_manager.broadcast_to_factory(factory_id, payload)
