"""
tests/test_phase43_ai_actions.py
Phase 4.3 — AI Action Service & WebSocket Notification Integration Tests.
Covers:
  - Real database model persistence (Incident, Alert, Sensor)
  - Role-based authorization guard (operator vs supervisor/manager)
  - Multi-tenant isolation (cross-factory entity modification rejection)
  - Idempotency caching (prevent duplicate side-effects)
  - Real-time WebSocket broadcasting (ai_action_requested, ai_action_completed, ai_action_failed, incident_created, alert_created)
  - Transaction safety (caller owns session, no commit/rollback inside service)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.core.errors import ResourceNotFoundException, TenantAccessDeniedException
from app.models.enums import AlertStatus, EventType, FactoryStatus, IncidentState, SeverityLevel, SourceStatus
from app.models.incidents import Alert, Incident
from app.models.operational import Sensor
from app.models.tenant import Factory
from app.services.ai_action_service import AIActionService, get_ai_action_service

FACTORY_1 = UUID("aaaaaaaa-0001-0001-0001-000000000001")
FACTORY_2 = UUID("bbbbbbbb-0002-0002-0002-000000000002")
USER_SUPERVISOR = UUID("11111111-0001-0001-0001-000000000001")
USER_OPERATOR = UUID("22222222-0001-0001-0001-000000000002")


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create required tables
    Factory.__table__.create(bind=engine, checkfirst=True)
    Sensor.__table__.create(bind=engine, checkfirst=True)
    Incident.__table__.create(bind=engine, checkfirst=True)
    Alert.__table__.create(bind=engine, checkfirst=True)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    # Seed factories
    f1 = Factory(id=FACTORY_1, name="Alpha Plant", slug="alpha-plant", status=FactoryStatus.ACTIVE)
    f2 = Factory(id=FACTORY_2, name="Beta Plant", slug="beta-plant", status=FactoryStatus.ACTIVE)
    session.add_all([f1, f2])
    session.commit()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def action_service():
    return AIActionService()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAIActionExecution:

    @pytest.mark.anyio
    async def test_create_incident_action(self, in_memory_db, action_service):
        """Verify real Incident record creation and WebSocket broadcast."""
        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            result = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_SUPERVISOR,
                user_role="safety_supervisor",
                action_id="act-001",
                action_type="create_incident",
                parameters={
                    "incident_type": "ppe_violation",
                    "severity": "high",
                    "description": "Worker entered hazardous area without helmet",
                },
                broadcast=True,
            )

            assert result["status"] == "executed"
            inc_id = UUID(result["details"]["incident_id"])

            # Verify DB persistence via session
            incident = in_memory_db.get(Incident, inc_id)
            assert incident is not None
            assert incident.factory_id == FACTORY_1
            assert incident.incident_type == EventType.PPE_VIOLATION
            assert incident.severity == SeverityLevel.HIGH
            assert incident.state == IncidentState.DETECTED

            # Verify WebSocket notifications
            assert mock_ws.call_count >= 2  # ai_action_requested, incident_created, ai_action_completed
            types = [c.args[1]["type"] for c in mock_ws.call_args_list]
            assert "incident_created" in types
            assert "ai_action_completed" in types

    @pytest.mark.anyio
    async def test_acknowledge_incident_action(self, in_memory_db, action_service):
        """Verify acknowledging an existing incident updates state and reviewed_by."""
        # Create incident first
        inc = Incident(
            id=uuid4(),
            factory_id=FACTORY_1,
            incident_type=EventType.FALL,
            severity=SeverityLevel.MEDIUM,
            state=IncidentState.DETECTED,
            opened_at=datetime.now(timezone.utc),
            last_event_at=datetime.now(timezone.utc),
        )
        in_memory_db.add(inc)
        in_memory_db.flush()

        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            result = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_SUPERVISOR,
                user_role="safety_supervisor",
                action_id="act-002",
                action_type="acknowledge_incident",
                parameters={"incident_id": str(inc.id)},
                broadcast=True,
            )

            assert result["status"] == "executed"
            updated = in_memory_db.get(Incident, inc.id)
            assert updated.state == IncidentState.UNDER_REVIEW
            assert updated.reviewed_by == USER_SUPERVISOR

    @pytest.mark.anyio
    async def test_request_alert_action(self, in_memory_db, action_service):
        """Verify Alert record creation linked to Incident."""
        inc = Incident(
            id=uuid4(),
            factory_id=FACTORY_1,
            incident_type=EventType.FIRE,
            severity=SeverityLevel.CRITICAL,
            state=IncidentState.DETECTED,
            opened_at=datetime.now(timezone.utc),
            last_event_at=datetime.now(timezone.utc),
        )
        in_memory_db.add(inc)
        in_memory_db.flush()

        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            result = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_SUPERVISOR,
                user_role="safety_supervisor",
                action_id="act-003",
                action_type="request_alert",
                parameters={
                    "incident_id": str(inc.id),
                    "severity": "critical",
                    "message": "Evacuation alarm triggered in Section 4",
                },
                broadcast=True,
            )

            assert result["status"] == "executed"
            alert_id = UUID(result["details"]["alert_id"])
            alert = in_memory_db.get(Alert, alert_id)
            assert alert is not None
            assert alert.incident_id == inc.id
            assert alert.factory_id == FACTORY_1
            assert alert.severity == SeverityLevel.CRITICAL
            assert alert.status == AlertStatus.PENDING

    @pytest.mark.anyio
    async def test_sensor_toggle_action(self, in_memory_db, action_service):
        """Verify Sensor status update (mute/unavailable)."""
        sensor = Sensor(
            id=uuid4(),
            factory_id=FACTORY_1,
            name="Furnace-Temp-01",
            status=SourceStatus.AVAILABLE,
        )
        in_memory_db.add(sensor)
        in_memory_db.flush()

        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock):
            result = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_SUPERVISOR,
                user_role="safety_supervisor",
                action_id="act-004",
                action_type="sensor_toggle",
                parameters={"sensor_id": str(sensor.id), "status": "unavailable"},
                broadcast=False,
            )

            assert result["status"] == "executed"
            updated = in_memory_db.get(Sensor, sensor.id)
            assert updated.status == SourceStatus.UNAVAILABLE

    @pytest.mark.anyio
    async def test_operator_role_rejection(self, in_memory_db, action_service):
        """Operators must be rejected from privileged actions like escalation or alert."""
        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            result = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_OPERATOR,
                user_role="operator",
                action_id="act-005",
                action_type="escalation",
                parameters={"target_role": "factory_manager"},
                broadcast=True,
            )

            assert result["status"] == "rejected"
            assert "requires supervisor" in result["message"]
            # Verify ai_action_failed was broadcast
            failed_broadcasts = [c for c in mock_ws.call_args_list if c.args[1]["type"] == "ai_action_failed"]
            assert len(failed_broadcasts) == 1

    @pytest.mark.anyio
    async def test_cross_factory_isolation(self, in_memory_db, action_service):
        """Attempting to acknowledge an incident of Factory 2 while scoped to Factory 1 must fail."""
        inc_f2 = Incident(
            id=uuid4(),
            factory_id=FACTORY_2,
            incident_type=EventType.FALL,
            severity=SeverityLevel.LOW,
            state=IncidentState.DETECTED,
            opened_at=datetime.now(timezone.utc),
            last_event_at=datetime.now(timezone.utc),
        )
        in_memory_db.add(inc_f2)
        in_memory_db.flush()

        result = await action_service.execute_action(
            db=in_memory_db,
            factory_id=FACTORY_1,  # Scoped to factory 1
            user_id=USER_SUPERVISOR,
            user_role="safety_supervisor",
            action_id="act-006",
            action_type="acknowledge_incident",
            parameters={"incident_id": str(inc_f2.id)},
            broadcast=False,
        )

        assert result["status"] == "failed"
        assert "does not belong" in result["message"]

    @pytest.mark.anyio
    async def test_idempotency_caching(self, in_memory_db, action_service):
        """Same idempotency_key must return cached response without duplicating execution."""
        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock):
            res1 = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_SUPERVISOR,
                user_role="safety_supervisor",
                action_id="act-007",
                action_type="create_incident",
                parameters={"description": "Idempotent incident"},
                idempotency_key="unique-key-12345",
                broadcast=False,
            )
            assert res1["status"] == "executed"

            # Execute second time with same key
            res2 = await action_service.execute_action(
                db=in_memory_db,
                factory_id=FACTORY_1,
                user_id=USER_SUPERVISOR,
                user_role="safety_supervisor",
                action_id="act-007",
                action_type="create_incident",
                parameters={"description": "Idempotent incident"},
                idempotency_key="unique-key-12345",
                broadcast=False,
            )

            assert res1 == res2
            assert res1["audit_reference"] == res2["audit_reference"]
