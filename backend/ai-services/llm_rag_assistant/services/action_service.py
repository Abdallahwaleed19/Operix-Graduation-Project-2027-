"""
services/action_service.py
Validation and delegation adapter for agentic remediation actions.

IMPORTANT:
  - Mock/hardcoded operational execution has been removed from production paths.
  - All real operational actions MUST be executed through the centralized
    canonical Backend AIActionService (app.services.ai_action_service.AIActionService).
  - This module validates action types, parameters, and RBAC before delegating.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional
from uuid import UUID

from ..schemas.contracts import ActionExecutionRequest, ActionExecutionResponse

logger = logging.getLogger("OperixActionService")

SUPPORTED_ACTION_TYPES: frozenset[str] = frozenset({
    "create_incident",
    "acknowledge_incident",
    "investigate_incident",
    "alert",
    "request_alert",
    "sensor_toggle",
    "mute_sensor",
    "maintenance",
    "dispatch",
    "escalation",
})

PRIVILEGED_ACTION_TYPES: frozenset[str] = frozenset({
    "escalation",
    "alert",
    "request_alert",
    "sensor_toggle",
    "mute_sensor",
    "create_incident",
})


class OperixActionService:
    """
    Action parameter validator and delegation coordinator for the centralized
    Backend AIActionService. Never mutates operational DB tables directly.
    """

    def __init__(self, audit_callback: Optional[Callable[[dict[str, Any]], None]] = None) -> None:
        self._execution_history: Deque[dict[str, Any]] = deque(maxlen=1000)
        self._idempotency_cache: dict[str, ActionExecutionResponse] = {}
        self.audit_callback = audit_callback

    def validate_request(
        self,
        request: ActionExecutionRequest,
        *,
        authenticated_factory_id: Optional[UUID] = None,
        authenticated_user_id: Optional[UUID] = None,
        authenticated_role: Optional[str] = None,
    ) -> str:
        """
        Validate action_type, parameters, and RBAC.
        Returns normalized action_type or raises ValueError / PermissionError.
        """
        action_type = request.action_type.strip().lower()
        if action_type not in SUPPORTED_ACTION_TYPES:
            raise ValueError(f"Unsupported action_type '{request.action_type}'.")

        role = (authenticated_role or request.user_role or "").strip().lower()
        if role in ("operator", "worker") and action_type in PRIVILEGED_ACTION_TYPES:
            raise PermissionError(
                f"Action '{action_type}' rejected: requires supervisor or factory_manager privileges."
            )

        if not isinstance(request.parameters, dict):
            raise ValueError("Action parameters must be a JSON object/dict.")

        if action_type in ("acknowledge_incident", "investigate_incident", "alert", "request_alert"):
            inc_id = request.parameters.get("incident_id")
            if not inc_id:
                raise ValueError(f"Action '{action_type}' requires 'incident_id' parameter.")
            UUID(str(inc_id))

        if action_type in ("sensor_toggle", "mute_sensor"):
            sensor_id = request.parameters.get("sensor_id")
            if not sensor_id:
                raise ValueError(f"Action '{action_type}' requires 'sensor_id' parameter.")
            UUID(str(sensor_id))

        return action_type

    def execute(self, request: ActionExecutionRequest) -> ActionExecutionResponse:
        """
        Direct mock execution is disabled.
        Operational actions must be delegated through execute_with_backend()
        using the centralized Backend AIActionService.
        """
        self.validate_request(request)
        raise RuntimeError(
            "Direct mock action execution is disabled in production. "
            "Use the centralized Backend AIActionService via execute_with_backend()."
        )

    async def execute_with_backend(
        self,
        *,
        backend_action_service: Any,
        db: Any,
        factory_id: UUID,
        user_id: UUID,
        user_role: str,
        request: ActionExecutionRequest,
        broadcast: bool = True,
        defer_broadcast: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate request and delegate execution to the canonical Backend AIActionService.
        Always uses authenticated factory_id, user_id, and user_role (never trusts payload identity).
        Caller owns the DB session (never commits, rolls back, or closes).
        """
        norm_type = self.validate_request(
            request,
            authenticated_factory_id=factory_id,
            authenticated_user_id=user_id,
            authenticated_role=user_role,
        )
        result = await backend_action_service.execute_action(
            db=db,
            factory_id=factory_id,
            user_id=user_id,
            user_role=user_role,
            action_id=request.action_id,
            action_type=norm_type,
            parameters=request.parameters,
            idempotency_key=request.idempotency_key,
            confirmed_by=request.confirmed_by,
            broadcast=broadcast,
            defer_broadcast=defer_broadcast,
            raise_on_error=True,
        )
        record = {
            "audit_reference": result.get("audit_reference"),
            "action_id": request.action_id,
            "action_type": norm_type,
            "factory_id": str(factory_id),
            "user_id": str(user_id),
            "status": result.get("status"),
        }
        self._execution_history.append(record)
        if self.audit_callback:
            try:
                self.audit_callback(record)
            except Exception as audit_err:
                logger.warning(f"External audit callback failed: {audit_err}")
        return result

    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Return bounded history of delegated action records."""
        return list(self._execution_history)


_action_service = OperixActionService()


def get_action_service() -> OperixActionService:
    """Dependency injection helper."""
    return _action_service
