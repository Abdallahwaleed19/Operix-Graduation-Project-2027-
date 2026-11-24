"""
app/services/ai_action_service.py
Phase 4.3 — Real Backend AI Action Service & WebSocket Notification Integration.

Connects AI-generated action requests to real canonical database models
(Incident, Alert, Sensor) and broadcasts real-time WebSocket notifications.
Eliminates mock-only execution while respecting caller-owned transactions and
strict multi-tenant isolation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from ..core.errors import OperixException, ResourceNotFoundException, TenantAccessDeniedException
from ..core.logging import logger
from ..core.security import AuthorizationException
from ..core.websocket import ws_manager
from ..models.enums import (
    AlertStatus,
    EventType,
    IncidentState,
    SeverityLevel,
    SourceStatus,
)
from ..models.incidents import Alert, Incident
from ..models.operational import Sensor

logger = logging.getLogger("AIActionService")


class AIActionService:
    """
    Canonical backend service executing AI-proposed remediation actions.
    Enforces tenant boundaries, role privileges, transaction safety, and WebSockets.
    """

    def __init__(self) -> None:
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}
        self._execution_history: list[dict[str, Any]] = []

    async def execute_action(
        self,
        db: Session,
        factory_id: UUID,
        user_id: UUID,
        user_role: str,
        action_id: str,
        action_type: str,
        parameters: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        confirmed_by: Optional[str] = None,
        broadcast: bool = True,
        defer_broadcast: bool = False,
        raise_on_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an authorized remediation action against real canonical models.
        Caller owns the DB session (we do NOT commit, rollback, or close).
        If defer_broadcast=True, success events are staged into _pending_broadcasts
        so the caller can broadcast strictly post-commit.
        If raise_on_error=True, exceptions are propagated to trigger session rollback.
        """
        norm_action_type = action_type.strip().lower()

        # 1. Idempotency Check
        if idempotency_key and idempotency_key in self._idempotency_cache:
            logger.info(f"Returning cached action execution for key: {idempotency_key}")
            return self._idempotency_cache[idempotency_key]

        # 2. Role-based authorization guard
        # Operators cannot trigger escalations, alerts, sensor toggles, or incident creations
        privileged_actions = ("escalation", "alert", "request_alert", "sensor_toggle", "mute_sensor", "create_incident")
        if user_role.lower() in ("operator", "worker") and norm_action_type in privileged_actions:
            audit_ref = f"REJ-{uuid4().hex[:6].upper()}"
            rejection_result = {
                "action_id": action_id,
                "status": "rejected",
                "message": f"Action '{norm_action_type}' rejected: requires supervisor or factory_manager privileges.",
                "audit_reference": audit_ref,
                "details": {
                    "rejection_reason": "insufficient_role_privileges",
                    "user_role": user_role,
                    "required_roles": ["safety_supervisor", "factory_manager", "factory_admin"],
                },
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if broadcast and not defer_broadcast:
                await self._broadcast_status(factory_id, "ai_action_failed", rejection_result)
            if raise_on_error:
                raise AuthorizationException(rejection_result["message"], error_code="INSUFFICIENT_PERMISSIONS")
            return rejection_result

        # Broadcast 'ai_action_requested' immediately (audit of request)
        if broadcast and not defer_broadcast:
            await self._broadcast_status(
                factory_id,
                "ai_action_requested",
                {
                    "action_id": action_id,
                    "action_type": norm_action_type,
                    "initiated_by": str(user_id),
                    "parameters": parameters,
                },
            )

        audit_code = f"AUDIT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        details: Dict[str, Any] = {}
        msg = ""
        staged_broadcasts: list[tuple[UUID, Dict[str, Any]]] = []

        try:
            # 3. Dispatch to canonical handlers
            if norm_action_type == "create_incident":
                msg, details = await self._handle_create_incident(
                    db=db,
                    factory_id=factory_id,
                    user_id=user_id,
                    parameters=parameters,
                    broadcast=broadcast and not defer_broadcast,
                    staged_broadcasts=staged_broadcasts if defer_broadcast else None,
                )

            elif norm_action_type in ("acknowledge_incident", "investigate_incident"):
                msg, details = await self._handle_acknowledge_incident(
                    db=db,
                    factory_id=factory_id,
                    user_id=user_id,
                    parameters=parameters,
                )

            elif norm_action_type in ("alert", "request_alert"):
                msg, details = await self._handle_request_alert(
                    db=db,
                    factory_id=factory_id,
                    user_id=user_id,
                    parameters=parameters,
                    broadcast=broadcast and not defer_broadcast,
                    staged_broadcasts=staged_broadcasts if defer_broadcast else None,
                )

            elif norm_action_type in ("sensor_toggle", "mute_sensor"):
                msg, details = await self._handle_sensor_toggle(
                    db=db,
                    factory_id=factory_id,
                    parameters=parameters,
                )

            elif norm_action_type in ("maintenance", "dispatch", "escalation"):
                # Operational workflow tracking
                target = parameters.get("target") or parameters.get("zone_name") or parameters.get("department") or "Factory Zone"
                task_desc = parameters.get("task") or parameters.get("target_role") or "Operational remediation"
                msg = f"Remediation action [{norm_action_type.upper()}] registered for {target}: {task_desc}."
                details = {
                    "action_type": norm_action_type,
                    "target": target,
                    "task": task_desc,
                    "parameters": parameters,
                    "status": "dispatched",
                }

            else:
                msg = f"Generic action {action_id} ({norm_action_type}) recorded."
                details = {"generic_action": True, "parameters": parameters}

            # Record in execution history
            result: Dict[str, Any] = {
                "action_id": action_id,
                "status": "executed",
                "message": msg,
                "audit_reference": audit_code,
                "details": details,
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._execution_history.append({
                **result,
                "factory_id": str(factory_id),
                "user_id": str(user_id),
                "confirmed_by": confirmed_by or str(user_id),
            })

            # Broadcast 'ai_action_completed' post-commit or immediate
            completion_packet = {
                "type": "ai_action_completed",
                "factory_id": str(factory_id),
                "data": result,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

            if defer_broadcast:
                staged_broadcasts.append((factory_id, completion_packet))
                result["_pending_broadcasts"] = staged_broadcasts
            elif broadcast:
                await self._broadcast_status(factory_id, "ai_action_completed", result)

            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result

            return result

        except Exception as exc:
            logger.error(f"Error executing AI action {action_id} [{norm_action_type}]: {exc}")
            err_result: Dict[str, Any] = {
                "action_id": action_id,
                "status": "failed",
                "message": f"Action execution failed: {str(exc)}",
                "audit_reference": audit_code,
                "details": {"error_type": type(exc).__name__},
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if broadcast and not defer_broadcast:
                await self._broadcast_status(factory_id, "ai_action_failed", err_result)
            if raise_on_error:
                if isinstance(exc, OperixException):
                    raise exc
                raise OperixException(
                    message=f"Action execution failed: {str(exc)}",
                    status_code=400,
                    error_code="ACTION_EXECUTION_FAILED",
                ) from exc
            return err_result

    # -----------------------------------------------------------------------
    # Canonical Handlers
    # -----------------------------------------------------------------------

    async def _handle_create_incident(
        self,
        db: Session,
        factory_id: UUID,
        user_id: UUID,
        parameters: Dict[str, Any],
        broadcast: bool,
        staged_broadcasts: Optional[list[tuple[UUID, Dict[str, Any]]]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Create a real Incident in the database."""
        raw_type = parameters.get("incident_type", "ppe_violation")
        try:
            inc_type = EventType(raw_type)
        except ValueError:
            inc_type = EventType.PPE_VIOLATION

        raw_sev = parameters.get("severity", "medium")
        try:
            sev = SeverityLevel(raw_sev)
        except ValueError:
            sev = SeverityLevel.MEDIUM

        note = parameters.get("description") or parameters.get("resolution_note") or "AI Assistant created incident"

        incident = Incident(
            id=uuid4(),
            factory_id=factory_id,
            incident_type=inc_type,
            severity=sev,
            state=IncidentState.DETECTED,
            opened_at=datetime.now(timezone.utc),
            last_event_at=datetime.now(timezone.utc),
            resolution_note=note,
        )
        db.add(incident)
        db.flush()

        msg = f"Incident created successfully [ID: {incident.id}, Type: {inc_type.value}, Severity: {sev.value}]."
        details = {
            "incident_id": str(incident.id),
            "incident_type": inc_type.value,
            "severity": sev.value,
            "state": incident.state.value,
            "opened_at": incident.opened_at.isoformat(),
        }

        ws_packet = {
            "type": "incident_created",
            "factory_id": str(factory_id),
            "data": details,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        # WebSocket broadcast for incident creation (staged or immediate)
        if staged_broadcasts is not None:
            staged_broadcasts.append((factory_id, ws_packet))
        elif broadcast:
            await ws_manager.broadcast_to_factory(factory_id, ws_packet)

        return msg, details

    async def _handle_acknowledge_incident(
        self,
        db: Session,
        factory_id: UUID,
        user_id: UUID,
        parameters: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        """Acknowledge / review an existing Incident."""
        inc_id_raw = parameters.get("incident_id")
        if not inc_id_raw:
            raise ValueError("Missing 'incident_id' parameter.")

        inc_id = UUID(str(inc_id_raw))
        incident = db.get(Incident, inc_id)
        if incident is None:
            raise ResourceNotFoundException("incident", f"Incident '{inc_id}' not found.")

        # Multi-tenant boundary check
        if incident.factory_id != factory_id:
            raise TenantAccessDeniedException(f"Incident '{inc_id}' does not belong to tenant factory.")

        incident.state = IncidentState.UNDER_REVIEW
        incident.reviewed_by = user_id
        incident.reviewed_at = datetime.now(timezone.utc)
        db.flush()

        msg = f"Incident {inc_id} acknowledged and state set to 'under_review'."
        details = {
            "incident_id": str(inc_id),
            "state": incident.state.value,
            "reviewed_by": str(user_id),
            "reviewed_at": incident.reviewed_at.isoformat(),
        }
        return msg, details

    async def _handle_request_alert(
        self,
        db: Session,
        factory_id: UUID,
        user_id: UUID,
        parameters: Dict[str, Any],
        broadcast: bool,
        staged_broadcasts: Optional[list[tuple[UUID, Dict[str, Any]]]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Create a real Alert linked to an Incident."""
        inc_id_raw = parameters.get("incident_id")
        if not inc_id_raw:
            raise ValueError("Missing 'incident_id' for alert creation.")

        inc_id = UUID(str(inc_id_raw))
        incident = db.get(Incident, inc_id)
        if incident is None:
            raise ResourceNotFoundException("incident", f"Incident '{inc_id}' not found.")

        # Multi-tenant boundary check
        if incident.factory_id != factory_id:
            raise TenantAccessDeniedException(f"Incident '{inc_id}' does not belong to tenant factory.")

        raw_sev = parameters.get("severity", incident.severity.value)
        try:
            sev = SeverityLevel(raw_sev)
        except ValueError:
            sev = incident.severity

        alert_msg = parameters.get("message") or f"Safety alert for incident {inc_id}"

        alert = Alert(
            id=uuid4(),
            factory_id=factory_id,
            incident_id=inc_id,
            severity=sev,
            message=alert_msg,
            status=AlertStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.flush()

        msg = f"Alert requested successfully [ID: {alert.id}, Incident: {inc_id}]."
        details = {
            "alert_id": str(alert.id),
            "incident_id": str(inc_id),
            "severity": sev.value,
            "status": alert.status.value,
            "created_at": alert.created_at.isoformat(),
        }

        ws_packet = {
            "type": "alert_created",
            "factory_id": str(factory_id),
            "data": details,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        # WebSocket broadcast for alert creation (staged or immediate)
        if staged_broadcasts is not None:
            staged_broadcasts.append((factory_id, ws_packet))
        elif broadcast:
            await ws_manager.broadcast_to_factory(factory_id, ws_packet)

        return msg, details

    async def _handle_sensor_toggle(
        self,
        db: Session,
        factory_id: UUID,
        parameters: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        """Mute / unmute / toggle status of a physical Sensor."""
        sensor_id_raw = parameters.get("sensor_id")
        if not sensor_id_raw:
            raise ValueError("Missing 'sensor_id' parameter.")

        sensor_id = UUID(str(sensor_id_raw))
        sensor = db.get(Sensor, sensor_id)
        if sensor is None:
            raise ResourceNotFoundException("sensor", f"Sensor '{sensor_id}' not found.")

        # Multi-tenant boundary check
        if sensor.factory_id != factory_id:
            raise TenantAccessDeniedException(f"Sensor '{sensor_id}' does not belong to tenant factory.")

        target_status_raw = parameters.get("status", "unavailable").lower()
        if target_status_raw in ("available", "online", "active"):
            new_status = SourceStatus.AVAILABLE
        elif target_status_raw in ("connecting", "recovering"):
            new_status = SourceStatus.CONNECTING
        elif target_status_raw == "configured":
            new_status = SourceStatus.CONFIGURED
        else:
            new_status = SourceStatus.UNAVAILABLE

        sensor.status = new_status
        db.flush()

        msg = f"Sensor {sensor_id} ({sensor.name}) status updated to '{new_status.value}'."
        details = {
            "sensor_id": str(sensor_id),
            "sensor_name": sensor.name,
            "new_status": new_status.value,
        }
        return msg, details

    # -----------------------------------------------------------------------
    # Helper: WebSocket Broadcast
    # -----------------------------------------------------------------------

    async def _broadcast_status(self, factory_id: UUID, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast status packet to the factory WebSocket room safely."""
        packet = {
            "type": event_type,
            "factory_id": str(factory_id),
            "data": data,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await ws_manager.broadcast_to_factory(factory_id, packet)
        except Exception as exc:
            logger.warning(f"Non-fatal error broadcasting {event_type} to factory {factory_id}: {exc}")

    async def broadcast_pending_events(self, pending_events: list[tuple[UUID, Dict[str, Any]]]) -> None:
        """
        Broadcast all staged events to factory rooms.
        Executed strictly post-commit via FastAPI BackgroundTasks.
        """
        for target_factory_id, packet in pending_events:
            try:
                await ws_manager.broadcast_to_factory(target_factory_id, packet)
            except Exception as exc:
                logger.warning(f"Non-fatal error in post-commit deferred broadcast {packet.get('type')}: {exc}")


_action_service_instance: Optional[AIActionService] = None


def get_ai_action_service() -> AIActionService:
    """Singleton getter for AIActionService."""
    global _action_service_instance
    if _action_service_instance is None:
        _action_service_instance = AIActionService()
    return _action_service_instance
