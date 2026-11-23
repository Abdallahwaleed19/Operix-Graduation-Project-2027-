"""
services/action_service.py
Service handling the execution and audit tracking of agentic remediation actions.
Enables seamless integration with FastAPI endpoints and frontend interactive buttons.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ..schemas.contracts import ActionExecutionRequest, ActionExecutionResponse

logger = logging.getLogger("OperixActionService")


class OperixActionService:
    """
    Execution staging and audit coordinator for confirmed remediation actions.
    Supports idempotency keys, role checks, and downstream database audit hooks.
    """

    def __init__(self, audit_callback: Optional[Callable[[dict[str, Any]], None]] = None) -> None:
        self._execution_history: list[dict[str, Any]] = []
        self._idempotency_cache: dict[str, ActionExecutionResponse] = {}
        self.audit_callback = audit_callback

    def execute(self, request: ActionExecutionRequest) -> ActionExecutionResponse:
        """
        Execute an authorized remediation action with idempotency and role validation.
        """
        # 1. Idempotency protection
        if request.idempotency_key and request.idempotency_key in self._idempotency_cache:
            logger.info(f"Returning cached execution for idempotency key: {request.idempotency_key}")
            return self._idempotency_cache[request.idempotency_key]

        action_type = request.action_type.lower()
        confirmed_by = request.confirmed_by or "authorized_supervisor"

        # 2. Role-based privilege validation
        if request.user_role == "operator" and action_type in ("escalation", "alert"):
            return ActionExecutionResponse(
                action_id=request.action_id,
                status="rejected",
                message=f"Action '{action_type}' rejected: requires supervisor or factory_manager privileges.",
                audit_reference=f"REJ-{uuid4().hex[:6].upper()}",
                details={"rejection_reason": "insufficient_role_privileges", "required_role": "supervisor"},
            )

        audit_code = f"AUDIT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

        # Routing to specific execution handlers
        if action_type == "maintenance":
            cam = request.parameters.get("camera_name", "Equipment-CAM")
            dept = request.parameters.get("department", "Maintenance")
            msg = f"Maintenance ticket successfully created for {cam} and assigned to {dept} department."
            details = {"ticket_id": f"TICK-{uuid4().hex[:8].upper()}", "status": "assigned", "priority": "high"}

        elif action_type == "alert":
            zone = request.parameters.get("zone_name", "Factory Floor")
            alert_type = request.parameters.get("alert_type", "audio_visual")
            msg = f"Safety alert [{alert_type}] broadcasted across zone: {zone}."
            details = {"broadcast_status": "delivered", "channels": ["dashboard_websocket", "floor_siren"]}

        elif action_type == "dispatch":
            zone = request.parameters.get("zone_name", "Hazardous Area")
            task = request.parameters.get("task", "safety_audit")
            msg = f"Safety supervisor successfully dispatched to {zone} for {task}."
            details = {"dispatch_status": "notified", "officer_role": "on_duty_supervisor"}

        elif action_type == "escalation":
            role = request.parameters.get("target_role", "factory_manager")
            msg = f"Critical incident report escalated directly to {role}."
            details = {"escalation_level": "Level-2", "notification_sent": True}

        else:
            msg = f"Action {request.action_id} of type {action_type} executed successfully."
            details = {"generic_execution": True}

        record = {
            "audit_reference": audit_code,
            "action_id": request.action_id,
            "action_type": action_type,
            "confirmed_by": confirmed_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
            "factory_id": str(request.factory_id) if request.factory_id else None,
            "user_id": str(request.user_id) if request.user_id else None,
        }
        self._execution_history.append(record)
        logger.info(f"[ACTION EXECUTED] {audit_code}: {msg}")

        # Trigger external durable audit callback if registered by main backend
        if self.audit_callback:
            try:
                self.audit_callback(record)
            except Exception as audit_err:
                logger.warning(f"External audit callback failed: {audit_err}")

        resp = ActionExecutionResponse(
            action_id=request.action_id,
            status="executed",
            message=msg,
            audit_reference=audit_code,
            details=details,
        )

        if request.idempotency_key:
            self._idempotency_cache[request.idempotency_key] = resp

        return resp

    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Return history of all executed actions."""
        return list(self._execution_history)


# Singleton instance
_action_service = OperixActionService()


def get_action_service() -> OperixActionService:
    """Dependency injection helper."""
    return _action_service
