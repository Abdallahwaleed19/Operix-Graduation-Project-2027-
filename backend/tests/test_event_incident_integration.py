"""
tests/test_event_incident_integration.py
Phase 3.5: Event & Incident Integration Tests:
- Rule evaluation integration on event ingestion.
- Primary rule_id persistence and details['rule_evaluation'] enrichment.
- Duplicate event idempotency and skip of re-evaluation.
- Incident association preservation when incident_id is present.
- Alert safety: notify=True flag reflected in response and WS without rogue DB alerts.
- Multi-tenant boundary isolation.
- WebSocket broadcast payload validation.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.enums import CameraType, EventType, FactoryStatus, IncidentState, SeverityLevel, ZoneType
from app.models.incidents import Alert, Event, Incident
from app.models.operational import Camera, Department, MonitoringZone, SafetyRule, Sensor
from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User
from app.schemas.events import CVEventIngest
from app.services.event_service import EventService
from app.services.rule_evaluation_service import RuleEvaluationService


CV_AUTH_HEADERS = {"X-Camera-Key": settings.DEFAULT_CV_API_KEY}


@pytest.fixture(scope="module")
def setup_integration_tables():
    """Ensure required tables exist in test SQLite database."""
    tables = [
        Factory.__table__,
        Role.__table__,
        User.__table__,
        AuthToken.__table__,
        FactoryMembership.__table__,
        Department.__table__,
        Camera.__table__,
        Sensor.__table__,
        MonitoringZone.__table__,
        SafetyRule.__table__,
        Incident.__table__,
        Event.__table__,
        Alert.__table__,
    ]
    for table in tables:
        table.create(bind=engine, checkfirst=True)
    yield


@pytest.fixture
def integration_env(setup_integration_tables):
    """Seed test operational hierarchy."""
    db = SessionLocal()
    f1_id = uuid.uuid4()
    f2_id = uuid.uuid4()

    try:
        f1 = Factory(id=f1_id, name="Factory Alpha", slug=f"f-alpha-{f1_id.hex[:6]}", status=FactoryStatus.ACTIVE)
        f2 = Factory(id=f2_id, name="Factory Beta", slug=f"f-beta-{f2_id.hex[:6]}", status=FactoryStatus.ACTIVE)
        db.add_all([f1, f2])

        dept1 = Department(id=uuid.uuid4(), factory_id=f1_id, name="Assembly Area")
        db.add(dept1)

        cam1 = Camera(
            id=uuid.uuid4(),
            factory_id=f1_id,
            department_id=dept1.id,
            name="Camera Alpha 1",
            camera_type=CameraType.CCTV,
            stream_url_ref="rtsp://dummy/cam_alpha1",
        )
        db.add(cam1)

        dept1_id = dept1.id
        cam1_id = cam1.id

        db.commit()
        db.close()

        yield {
            "f1_id": f1_id,
            "f2_id": f2_id,
            "dept1_id": dept1_id,
            "cam1_id": cam1_id,
        }
    finally:
        pass


@pytest.mark.anyio
async def test_event_ingestion_integrates_rule_evaluation_and_primary_rule(integration_env):
    """
    Verify:
    1. Event ingestion persists event.
    2. Rule evaluation executes and matches rule.
    3. Event.rule_id is set to primary match.
    4. Event.details contains 'rule_evaluation' metadata.
    5. EventIngestResponse includes rule_id, matched_rules_count, and should_notify.
    """
    db = SessionLocal()
    f1_id = integration_env["f1_id"]
    cam1_id = integration_env["cam1_id"]
    event_id = uuid.uuid4()

    try:
        # Create an active rule with notify=True
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Alpha High Severity PPE",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            min_confidence=0.75,
            notify=True,
            is_enabled=True,
        )
        db.add(rule)
        db.commit()

        cv_event = CVEventIngest(
            event_id=event_id,
            event_type="ppe_violation",
            event_state="started",
            module="ppe_detector",
            camera_id=str(cam1_id),
            timestamp=datetime.now(timezone.utc),
            confidence=0.90,
            attributes={"missing": ["helmet"]},
        )

        # Ingest event
        res = await EventService.ingest_event(
            event_in=cv_event,
            factory_id=f1_id,
            db=db,
            broadcast=False,
        )

        assert res.status == "ingested"
        assert res.persisted is True
        assert res.rule_id == rule.id
        assert res.matched_rules_count == 1
        assert res.should_notify is True

        # Verify DB persistence of rule_id and details
        persisted = db.get(Event, event_id)
        assert persisted is not None
        assert persisted.rule_id == rule.id
        assert "rule_evaluation" in persisted.details
        eval_meta = persisted.details["rule_evaluation"]
        assert eval_meta["status"] == "evaluated"
        assert eval_meta["matched_count"] == 1
        assert eval_meta["should_notify"] is True
        assert eval_meta["primary_rule_id"] == str(rule.id)
    finally:
        db.rollback()
        db.close()


@pytest.mark.anyio
async def test_duplicate_event_skips_evaluation_and_preserves_idempotency(integration_env):
    """
    Verify:
    1. First ingestion evaluates rule.
    2. Duplicate ingestion returns 'duplicate_ignored' and skips re-evaluation.
    3. Existing rule_id is returned without duplicate side-effects.
    """
    db = SessionLocal()
    f1_id = integration_env["f1_id"]
    cam1_id = integration_env["cam1_id"]
    event_id = uuid.uuid4()

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Idempotency Test Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.MEDIUM,
            min_confidence=0.60,
            is_enabled=True,
        )
        db.add(rule)
        db.commit()

        cv_event = CVEventIngest(
            event_id=event_id,
            event_type="ppe_violation",
            event_state="started",
            module="ppe_detector",
            camera_id=str(cam1_id),
            timestamp=datetime.now(timezone.utc),
            confidence=0.85,
        )

        # First ingestion
        res1 = await EventService.ingest_event(
            event_in=cv_event,
            factory_id=f1_id,
            db=db,
            broadcast=False,
        )
        assert res1.status == "ingested"
        assert res1.rule_id == rule.id
        assert res1.matched_rules_count == 1

        # Second ingestion (duplicate)
        res2 = await EventService.ingest_event(
            event_in=cv_event,
            factory_id=f1_id,
            db=db,
            broadcast=False,
        )
        assert res2.status == "duplicate_ignored"
        assert res2.broadcast is False
        assert res2.rule_id == rule.id
        assert res2.matched_rules_count == 0
        assert res2.should_notify is False
    finally:
        db.rollback()
        db.close()


def test_incident_association_propagates_into_rule_evaluation(integration_env):
    """
    Verify:
    When an Event is associated with an existing Incident (incident_id):
    1. Rule evaluation recognizes and associates event.incident_id.
    2. Generated RuleViolation contains incident_id.
    """
    db = SessionLocal()
    f1_id = integration_env["f1_id"]
    cam1_id = integration_env["cam1_id"]
    incident_id = uuid.uuid4()
    event_id = uuid.uuid4()

    try:
        # Create an existing Incident
        incident = Incident(
            id=incident_id,
            factory_id=f1_id,
            incident_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            state=IncidentState.DETECTED,
            opened_at=datetime.now(timezone.utc),
            last_event_at=datetime.now(timezone.utc),
        )
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Incident Association Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            is_enabled=True,
        )
        db.add_all([incident, rule])
        db.commit()

        # Create Event linked to this incident
        event = Event(
            id=event_id,
            factory_id=f1_id,
            camera_id=cam1_id,
            incident_id=incident_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.95,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(
            db=db,
            factory_id=f1_id,
            event=event,
        )

        assert len(res.violations) == 1
        violation = res.violations[0]
        assert violation.incident_id == incident_id
        assert violation.rule_id == rule.id
    finally:
        db.rollback()
        db.close()


def test_alert_safety_no_rogue_database_alerts_without_incident_or_policy(integration_env):
    """
    Verify Alert Safety:
    Even when a rule has notify=True, the system does NOT create rogue, unlinked Alert
    entities in the database without an approved Incident and notification dispatch policy.
    Total alerts in DB remain 0.
    """
    db = SessionLocal()
    f1_id = integration_env["f1_id"]
    cam1_id = integration_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Notify Alert Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            notify=True,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.99,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)
        assert len(res.matches) == 1
        assert res.matches[0].notify is True

        # Assert no alerts table rows were created arbitrarily
        alerts_count = db.execute(select(Alert).where(Alert.factory_id == f1_id)).scalars().all()
        assert len(alerts_count) == 0
    finally:
        db.rollback()
        db.close()


@pytest.mark.anyio
async def test_websocket_broadcast_contains_rule_incident_and_notify_payload(integration_env):
    """
    Verify that WebSocket broadcast packet includes rule_id, incident_id, and should_notify.
    """
    db = SessionLocal()
    f1_id = integration_env["f1_id"]
    cam1_id = integration_env["cam1_id"]
    event_id = uuid.uuid4()

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="WS Broadcast Rule",
            event_type=EventType.FALL,
            severity=SeverityLevel.HIGH,
            notify=True,
            is_enabled=True,
        )
        db.add(rule)
        db.commit()

        cv_event = CVEventIngest(
            event_id=event_id,
            event_type="fall",
            event_state="started",
            module="fall_detector",
            camera_id=str(cam1_id),
            timestamp=datetime.now(timezone.utc),
            confidence=0.92,
        )

        with patch("app.services.event_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_broadcast:
            mock_broadcast.return_value = 1  # 1 client connected

            res = await EventService.ingest_event(
                event_in=cv_event,
                factory_id=f1_id,
                db=db,
                broadcast=True,
            )

            assert res.status == "ingested"
            assert res.broadcast is True
            assert res.should_notify is True
            assert res.rule_id == rule.id

            mock_broadcast.assert_called_once()
            call_factory_id, ws_packet = mock_broadcast.call_args[0]
            assert call_factory_id == f1_id
            assert ws_packet["type"] == "safety_event"
            data = ws_packet["data"]
            assert data["rule_id"] == str(rule.id)
            assert data["should_notify"] is True
            assert "rule_evaluation" in data["details"]
            assert data["details"]["rule_evaluation"]["should_notify"] is True
    finally:
        db.rollback()
        db.close()
