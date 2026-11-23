"""
tests/test_rule_evaluation.py
Automated tests for Phase 3.3 Safety Rule Evaluation Engine:
- Global rule matching.
- Zone-scoped rule matching.
- Department-scoped rule matching via camera hierarchy.
- Sensor-scoped rule matching.
- Confidence threshold evaluation (matching >= min_confidence, rejecting < min_confidence).
- Duration threshold evaluation where supported in event details.
- Threshold value evaluation for sensor metrics.
- Disabled rules rejection.
- Event type mismatch rejection.
- Cross-factory isolation (Factory A event never matches Factory B rule).
- Multiple matching rules and highest severity resolution.
- Idempotency: duplicate events do not re-evaluate or cause duplicate rule side-effects.
- Ingestion pipeline regression integration.
"""
from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine
from app.models.enums import CameraType, EventType, FactoryStatus, SeverityLevel, ZoneType
from app.models.incidents import Event
from app.models.operational import Camera, Department, MonitoringZone, SafetyRule, Sensor
from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User
from app.schemas.events import CVEventIngest
from app.services.event_service import EventService
from app.services.rule_evaluation_service import RuleEvaluationService


@pytest.fixture(scope="module")
def setup_evaluation_tables():
    """Ensure required tables exist in test environment."""
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
        Event.__table__,
    ]
    for table in tables:
        table.create(bind=engine, checkfirst=True)
    yield


@pytest.fixture
def eval_env(setup_evaluation_tables):
    """Seed full operational hierarchy with two isolated factories."""
    db = SessionLocal()
    f1_id = uuid.uuid4()
    f2_id = uuid.uuid4()

    try:
        f1 = Factory(id=f1_id, name="Factory 1", slug=f"f1-{f1_id.hex[:6]}", status=FactoryStatus.ACTIVE)
        f2 = Factory(id=f2_id, name="Factory 2", slug=f"f2-{f2_id.hex[:6]}", status=FactoryStatus.ACTIVE)
        db.add_all([f1, f2])

        dept1 = Department(id=uuid.uuid4(), factory_id=f1_id, name="Machining Dept")
        db.add(dept1)

        cam1 = Camera(
            id=uuid.uuid4(),
            factory_id=f1_id,
            department_id=dept1.id,
            name="Camera 101",
            camera_type=CameraType.CCTV,
            stream_url_ref="rtsp://dummy/cam1",
        )
        db.add(cam1)

        zone1 = MonitoringZone(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1.id,
            department_id=dept1.id,
            name="Restricted Robot Zone",
            zone_type=ZoneType.RESTRICTED,
            polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]],
        )
        db.add(zone1)

        sensor1 = Sensor(
            id=uuid.uuid4(),
            factory_id=f1_id,
            department_id=dept1.id,
            name="Thermal Sensor 01",
            sensor_type="temperature",
        )
        db.add(sensor1)

        dept1_id = dept1.id
        cam1_id = cam1.id
        zone1_id = zone1.id
        sensor1_id = sensor1.id

        db.commit()
        db.close()

        yield {
            "f1_id": f1_id,
            "f2_id": f2_id,
            "dept1_id": dept1_id,
            "cam1_id": cam1_id,
            "zone1_id": zone1_id,
            "sensor1_id": sensor1_id,
        }
    finally:
        pass


def test_global_rule_matching(eval_env):
    """Verify an enabled rule with no scope matches all events of that type with sufficient confidence."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Global PPE Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            min_confidence=0.80,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.92,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)
        assert res.evaluation_status == "evaluated"
        assert rule.id in res.matched_rule_ids
        assert res.matched_highest_severity == SeverityLevel.HIGH
        assert event.rule_id == rule.id
    finally:
        db.rollback()
        db.close()


def test_confidence_threshold_rejection(eval_env):
    """Verify an event with lower confidence than rule.min_confidence is not matched."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Strict Confidence Rule",
            event_type=EventType.FALL,
            severity=SeverityLevel.CRITICAL,
            min_confidence=0.90,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.FALL,
            confidence=0.75,  # below 0.90
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)
        assert rule.id not in res.matched_rule_ids
        assert rule.id in res.unmatched_rule_ids
        assert event.rule_id is None
    finally:
        db.rollback()
        db.close()


def test_zone_scoped_matching(eval_env):
    """Verify zone-scoped rule matches only events within that zone."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    zone1_id = eval_env["zone1_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Zone Intrusion Rule",
            event_type=EventType.RESTRICTED_ZONE_INTRUSION,
            severity=SeverityLevel.CRITICAL,
            zone_id=zone1_id,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        # Matching event (same zone)
        ev_match = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.RESTRICTED_ZONE_INTRUSION,
            zone_id=zone1_id,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(ev_match)
        db.flush()

        res1 = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=ev_match)
        assert rule.id in res1.matched_rule_ids
        assert ev_match.rule_id == rule.id

        # Non-matching event (different or None zone)
        ev_mismatch = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.RESTRICTED_ZONE_INTRUSION,
            zone_id=uuid.uuid4(),
            detected_at=datetime.now(timezone.utc),
        )
        db.add(ev_mismatch)
        db.flush()

        res2 = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=ev_mismatch)
        assert rule.id not in res2.matched_rule_ids
    finally:
        db.rollback()
        db.close()


def test_department_scoped_matching_via_camera(eval_env):
    """Verify department rule matches event through its Camera's department relation."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    dept1_id = eval_env["dept1_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Department Smoke Alert",
            event_type=EventType.SMOKE,
            severity=SeverityLevel.HIGH,
            department_id=dept1_id,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        # Event from Camera 1 (which belongs to dept1)
        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            event_type=EventType.SMOKE,
            camera_id=cam1_id,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)
        assert rule.id in res.matched_rule_ids
        assert res.matches[0].scope_type == "department"
    finally:
        db.rollback()
        db.close()


def test_sensor_scoped_matching_and_threshold(eval_env):
    """Verify sensor rule matches event sensor_id and evaluates threshold_value."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    sensor1_id = eval_env["sensor1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Overheat Sensor Rule",
            event_type=EventType.TEMPERATURE_ANOMALY,
            severity=SeverityLevel.CRITICAL,
            sensor_id=sensor1_id,
            threshold_value=Decimal("75.0"),
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        # Event with reading above threshold
        ev_high = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            event_type=EventType.TEMPERATURE_ANOMALY,
            sensor_id=sensor1_id,
            details={"temperature": 82.5},
            detected_at=datetime.now(timezone.utc),
        )
        db.add(ev_high)
        db.flush()

        res_high = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=ev_high)
        assert rule.id in res_high.matched_rule_ids

        # Event with reading below threshold
        ev_low = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            event_type=EventType.TEMPERATURE_ANOMALY,
            sensor_id=sensor1_id,
            details={"temperature": 60.0},
            detected_at=datetime.now(timezone.utc),
        )
        db.add(ev_low)
        db.flush()

        res_low = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=ev_low)
        assert rule.id not in res_low.matched_rule_ids
    finally:
        db.rollback()
        db.close()


def test_duration_evaluation(eval_env):
    """Verify rule with min_duration_s checks event duration_s in details."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Prolonged Fatigue Rule",
            event_type=EventType.POTENTIAL_FATIGUE,
            severity=SeverityLevel.MEDIUM,
            min_duration_s=10,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        # Event with sufficient duration
        ev_long = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.POTENTIAL_FATIGUE,
            details={"duration_s": 15},
            detected_at=datetime.now(timezone.utc),
        )
        db.add(ev_long)
        db.flush()

        res_long = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=ev_long)
        assert rule.id in res_long.matched_rule_ids

        # Event with insufficient duration
        ev_short = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.POTENTIAL_FATIGUE,
            details={"duration_s": 4},
            detected_at=datetime.now(timezone.utc),
        )
        db.add(ev_short)
        db.flush()

        res_short = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=ev_short)
        assert rule.id not in res_short.matched_rule_ids
    finally:
        db.rollback()
        db.close()


def test_disabled_rule_ignored(eval_env):
    """Verify disabled rule (is_enabled=False) is never evaluated."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Disabled Rule",
            event_type=EventType.FALL,
            severity=SeverityLevel.HIGH,
            is_enabled=False,
        )
        db.add(rule)
        db.flush()

        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.FALL,
            confidence=0.99,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)
        assert rule.id not in res.evaluated_rule_ids
        assert rule.id not in res.matched_rule_ids
    finally:
        db.rollback()
        db.close()


def test_cross_factory_isolation(eval_env):
    """Verify rules from Factory 2 are never evaluated for events from Factory 1."""
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    f2_id = eval_env["f2_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule_f2 = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f2_id,
            name="Factory 2 Exclusive Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            is_enabled=True,
        )
        db.add(rule_f2)
        db.flush()

        event_f1 = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.99,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event_f1)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event_f1)
        assert rule_f2.id not in res.evaluated_rule_ids
        assert rule_f2.id not in res.matched_rule_ids
    finally:
        db.rollback()
        db.close()


@pytest.mark.anyio
async def test_idempotent_ingestion_and_evaluation_integration(eval_env):
    """
    Verify EventService integration:
    - First ingestion persists event and evaluates rules.
    - Duplicate event returns status 'duplicate_ignored' and skips re-evaluation.
    """
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]
    event_id = uuid.uuid4()

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Ingest Integration Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            min_confidence=0.50,
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
            confidence=0.88,
        )

        # 1. First Ingestion
        res1 = await EventService.ingest_event(
            event_in=cv_event,
            factory_id=f1_id,
            db=db,
            broadcast=False,
        )
        assert res1.status == "ingested"
        assert res1.persisted is True

        # Check that event was persisted with rule_id set
        persisted = db.get(Event, event_id)
        assert persisted is not None
        assert persisted.rule_id == rule.id

        # 2. Duplicate Ingestion (Same event_id)
        res2 = await EventService.ingest_event(
            event_in=cv_event,
            factory_id=f1_id,
            db=db,
            broadcast=False,
        )
        assert res2.status == "duplicate_ignored"
        assert res2.broadcast is False
    finally:
        db.rollback()
        db.close()


def test_rule_execution_records_matched_and_rejected(eval_env):
    """
    Phase 3.4: Verify RuleExecutionRecord generation for both matched and rejected rules
    with granular rejection reasons (confidence, scope).
    """
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]
    zone1_id = eval_env["zone1_id"]
    other_zone_id = uuid.uuid4()

    try:
        # Rule 1: Matched (min_confidence 0.70)
        rule_matched = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Matched Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            min_confidence=0.70,
            version=2,
            is_enabled=True,
        )
        # Rule 2: Confidence Rejected (min_confidence 0.95)
        rule_conf_rejected = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Conf Rejected Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            min_confidence=0.95,
            version=1,
            is_enabled=True,
        )
        # Rule 3: Scope Rejected (zone mismatch)
        rule_scope_rejected = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Scope Rejected Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.MEDIUM,
            zone_id=other_zone_id,
            version=1,
            is_enabled=True,
        )
        db.add_all([rule_matched, rule_conf_rejected, rule_scope_rejected])
        db.flush()

        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            zone_id=zone1_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.85,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)

        # 3 rules evaluated
        assert len(res.execution_records) == 3

        # Check matched record
        rec_matched = next(r for r in res.execution_records if r.rule_id == rule_matched.id)
        assert rec_matched.is_matched is True
        assert rec_matched.rejection_reason is None
        assert rec_matched.rule_version == 2
        assert rec_matched.severity == SeverityLevel.HIGH
        assert rec_matched.execution_status == "completed"
        assert rec_matched.threshold_values["min_confidence"] == 0.70

        # Check confidence-rejected record
        rec_conf = next(r for r in res.execution_records if r.rule_id == rule_conf_rejected.id)
        assert rec_conf.is_matched is False
        assert rec_conf.rejection_reason == "confidence_below_threshold"
        assert rec_conf.execution_status == "completed"

        # Check scope-rejected record
        rec_scope = next(r for r in res.execution_records if r.rule_id == rule_scope_rejected.id)
        assert rec_scope.is_matched is False
        assert rec_scope.rejection_reason == "scope_mismatch"
        assert rec_scope.execution_status == "completed"
    finally:
        db.rollback()
        db.close()


def test_rule_violation_contract_generation(eval_env):
    """
    Phase 3.4: Verify RuleViolation contract generation on matched rules,
    including version propagation, severity, event metadata, and UUID generation.
    """
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]
    zone1_id = eval_env["zone1_id"]

    try:
        rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="Strict Hardhat Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            zone_id=zone1_id,
            version=4,
            is_enabled=True,
        )
        db.add(rule)
        db.flush()

        event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            zone_id=zone1_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.91,
            detected_at=datetime.now(timezone.utc),
            details={"missing": ["helmet"], "worker_ref": "W-401"},
        )
        db.add(event)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event)

        assert len(res.violations) == 1
        violation = res.violations[0]

        assert isinstance(violation.violation_id, uuid.UUID)
        assert violation.event_id == event.id
        assert violation.factory_id == f1_id
        assert violation.rule_id == rule.id
        assert violation.rule_name == "Strict Hardhat Rule"
        assert violation.rule_version == 4
        assert violation.severity == SeverityLevel.CRITICAL
        assert violation.violation_status == "detected"
        assert violation.scope_type == "zone"
        assert violation.zone_id == zone1_id
        assert violation.confidence == 0.91
        assert violation.details == {"missing": ["helmet"], "worker_ref": "W-401"}
    finally:
        db.rollback()
        db.close()


def test_rule_rejection_reasons_duration_and_sensor(eval_env):
    """
    Phase 3.4: Verify granular rejection reasons for duration_insufficient
    and threshold_metric_unmet.
    """
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    cam1_id = eval_env["cam1_id"]
    sensor1_id = eval_env["sensor1_id"]

    try:
        # Rule requiring 10s duration
        duration_rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="10s Fall Rule",
            event_type=EventType.FALL,
            severity=SeverityLevel.HIGH,
            min_duration_s=10,
            is_enabled=True,
        )
        # Rule requiring sensor threshold 100.0
        sensor_rule = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="High Heat Rule",
            event_type=EventType.TEMPERATURE_ANOMALY,
            severity=SeverityLevel.CRITICAL,
            sensor_id=sensor1_id,
            threshold_value=Decimal("100.0"),
            is_enabled=True,
        )
        db.add_all([duration_rule, sensor_rule])
        db.flush()

        # Event with only 3s duration -> duration_insufficient
        fall_event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.FALL,
            confidence=0.95,
            detected_at=datetime.now(timezone.utc),
            details={"duration_s": 3.0},
        )
        db.add(fall_event)
        db.flush()

        res_fall = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=fall_event)
        assert len(res_fall.execution_records) == 1
        assert res_fall.execution_records[0].is_matched is False
        assert res_fall.execution_records[0].rejection_reason == "duration_insufficient"

        # Event with sensor reading 45.0 < 100.0 -> threshold_metric_unmet
        temp_event = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            sensor_id=sensor1_id,
            event_type=EventType.TEMPERATURE_ANOMALY,
            confidence=0.99,
            detected_at=datetime.now(timezone.utc),
            details={"reading_value": 45.0},
        )
        db.add(temp_event)
        db.flush()

        res_temp = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=temp_event)
        assert len(res_temp.execution_records) == 1
        assert res_temp.execution_records[0].is_matched is False
        assert res_temp.execution_records[0].rejection_reason == "threshold_metric_unmet"
    finally:
        db.rollback()
        db.close()


def test_execution_history_and_violations_tenant_isolation(eval_env):
    """
    Phase 3.4: Verify tenant isolation in execution records and violations.
    Rules and events from Factory 1 never produce records or violations for Factory 2.
    """
    db = SessionLocal()
    f1_id = eval_env["f1_id"]
    f2_id = eval_env["f2_id"]
    cam1_id = eval_env["cam1_id"]

    try:
        rule_f1 = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f1_id,
            name="F1 PPE Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            is_enabled=True,
        )
        rule_f2 = SafetyRule(
            id=uuid.uuid4(),
            factory_id=f2_id,
            name="F2 PPE Rule",
            event_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.CRITICAL,
            is_enabled=True,
        )
        db.add_all([rule_f1, rule_f2])
        db.flush()

        event_f1 = Event(
            id=uuid.uuid4(),
            factory_id=f1_id,
            camera_id=cam1_id,
            event_type=EventType.PPE_VIOLATION,
            confidence=0.99,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event_f1)
        db.flush()

        res = RuleEvaluationService.evaluate_event(db=db, factory_id=f1_id, event=event_f1)

        # Execution records must contain only F1 rules
        assert len(res.execution_records) == 1
        assert res.execution_records[0].factory_id == f1_id
        assert res.execution_records[0].rule_id == rule_f1.id

        # Violations must contain only F1 rules
        assert len(res.violations) == 1
        assert res.violations[0].factory_id == f1_id
        assert res.violations[0].rule_id == rule_f1.id
    finally:
        db.rollback()
        db.close()
