"""
tests/test_rules.py
Automated tests for Phase 3.2 Safety Rule Management:
- Creation, required field validation, and bounds checking.
- Scope exclusivity (at most one of zone_id, department_id, sensor_id).
- Cross-factory reference rejection and strict tenant isolation.
- Partial updates and rule version incrementation.
- Status toggle (is_enabled).
- Safe deletion behavior.
- Regression testing against SQLite testing DB.
"""
from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine
from app.models.enums import CameraType, EventType, FactoryStatus, SeverityLevel, UserStatus, ZoneType
from app.models.operational import Camera, Department, MonitoringZone, SafetyRule, Sensor
from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User
from app.schemas.rules import SafetyRuleCreate, SafetyRuleStatusUpdate, SafetyRuleUpdate
from app.services.rule_service import RuleService


@pytest.fixture(scope="module")
def setup_operational_tables():
    """Ensure operational tables are created in SQLite test environment."""
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
    ]
    for table in tables:
        table.create(bind=engine, checkfirst=True)
    yield


@pytest.fixture
def tenant_fixture(setup_operational_tables):
    """Seed a tenant factory and operational hierarchy for rule tests."""
    db = SessionLocal()
    factory_id = uuid.uuid4()
    other_factory_id = uuid.uuid4()

    try:
        # 1. Primary Factory
        f1 = Factory(id=factory_id, name="Factory A", slug=f"f-a-{factory_id.hex[:6]}", status=FactoryStatus.ACTIVE)
        db.add(f1)

        # 2. Second Factory for tenant isolation checks
        f2 = Factory(id=other_factory_id, name="Factory B", slug=f"f-b-{other_factory_id.hex[:6]}", status=FactoryStatus.ACTIVE)
        db.add(f2)

        # 3. Department in Factory A
        dept = Department(id=uuid.uuid4(), factory_id=factory_id, name="Assembly")
        db.add(dept)

        # 4. Department in Factory B
        other_dept = Department(id=uuid.uuid4(), factory_id=other_factory_id, name="Painting")
        db.add(other_dept)

        # 5. Camera in Factory A
        cam = Camera(
            id=uuid.uuid4(),
            factory_id=factory_id,
            department_id=dept.id,
            name="Cam A1",
            camera_type=CameraType.CCTV,
            stream_url_ref="rtsp://localhost/stream",
        )
        db.add(cam)

        # 6. Zone in Factory A
        zone = MonitoringZone(
            id=uuid.uuid4(),
            factory_id=factory_id,
            camera_id=cam.id,
            department_id=dept.id,
            name="Restricted Zone 1",
            zone_type=ZoneType.RESTRICTED,
            polygon=[[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]],
        )
        db.add(zone)

        db.commit()

        yield {
            "factory_id": factory_id,
            "other_factory_id": other_factory_id,
            "dept_id": dept.id,
            "other_dept_id": other_dept.id,
            "zone_id": zone.id,
        }
    finally:
        db.rollback()
        db.close()


def test_rule_creation_success(client: TestClient, tenant_fixture):
    """Verify creating a valid safety rule via API."""
    factory_id = tenant_fixture["factory_id"]
    zone_id = tenant_fixture["zone_id"]

    payload = {
        "name": "PPE Hardhat Rule",
        "event_type": "ppe_violation",
        "severity": "critical",
        "zone_id": str(zone_id),
        "min_confidence": 0.85,
        "min_duration_s": 5,
        "notify": True,
        "is_enabled": True,
    }

    resp = client.post(
        "/api/v1/rules",
        json=payload,
        headers={"X-Factory-Id": str(factory_id)},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["name"] == "PPE Hardhat Rule"
    assert data["event_type"] == "ppe_violation"
    assert data["severity"] == "critical"
    assert data["zone_id"] == str(zone_id)
    assert data["version"] == 1
    assert data["is_enabled"] is True


def test_rule_creation_scope_exclusivity(client: TestClient, tenant_fixture):
    """Verify that specifying both zone_id and department_id raises 422 error."""
    factory_id = tenant_fixture["factory_id"]
    zone_id = tenant_fixture["zone_id"]
    dept_id = tenant_fixture["dept_id"]

    payload = {
        "name": "Conflicting Scope Rule",
        "event_type": "fall",
        "severity": "high",
        "zone_id": str(zone_id),
        "department_id": str(dept_id),
    }

    resp = client.post(
        "/api/v1/rules",
        json=payload,
        headers={"X-Factory-Id": str(factory_id)},
    )
    assert resp.status_code == 422


def test_rule_creation_invalid_bounds(client: TestClient, tenant_fixture):
    """Verify validation for invalid confidence (> 1.0) and negative duration."""
    factory_id = tenant_fixture["factory_id"]

    # Invalid confidence > 1.0
    resp1 = client.post(
        "/api/v1/rules",
        json={"name": "Bad Confidence", "event_type": "fire", "severity": "critical", "min_confidence": 1.5},
        headers={"X-Factory-Id": str(factory_id)},
    )
    assert resp1.status_code == 422

    # Invalid negative duration
    resp2 = client.post(
        "/api/v1/rules",
        json={"name": "Bad Duration", "event_type": "fire", "severity": "critical", "min_duration_s": -2},
        headers={"X-Factory-Id": str(factory_id)},
    )
    assert resp2.status_code == 422


def test_cross_factory_reference_rejection(client: TestClient, tenant_fixture):
    """Verify referencing a department belonging to another factory is rejected (404/Not Found)."""
    factory_id = tenant_fixture["factory_id"]
    other_dept_id = tenant_fixture["other_dept_id"]

    payload = {
        "name": "Cross Factory Dept Rule",
        "event_type": "restricted_zone_intrusion",
        "severity": "medium",
        "department_id": str(other_dept_id),
    }

    resp = client.post(
        "/api/v1/rules",
        json=payload,
        headers={"X-Factory-Id": str(factory_id)},
    )
    # Rejection because department doesn't exist for Factory A
    assert resp.status_code == 404


def test_rule_list_and_tenant_isolation(client: TestClient, tenant_fixture):
    """Verify rules for Factory A cannot be seen by Factory B."""
    f1 = tenant_fixture["factory_id"]
    f2 = tenant_fixture["other_factory_id"]

    # Create rule in Factory A
    client.post(
        "/api/v1/rules",
        json={"name": "Rule For Factory A Only", "event_type": "smoke", "severity": "high"},
        headers={"X-Factory-Id": str(f1)},
    )

    # Query list from Factory A
    r1 = client.get("/api/v1/rules", headers={"X-Factory-Id": str(f1)})
    assert r1.status_code == 200
    items_a = r1.json()["data"]["items"]
    assert any(r["name"] == "Rule For Factory A Only" for r in items_a)

    # Query list from Factory B
    r2 = client.get("/api/v1/rules", headers={"X-Factory-Id": str(f2)})
    assert r2.status_code == 200
    items_b = r2.json()["data"]["items"]
    assert not any(r["name"] == "Rule For Factory A Only" for r in items_b)


def test_rule_update_and_version_increment(client: TestClient, tenant_fixture):
    """Verify partial updates increment rule version."""
    f1 = tenant_fixture["factory_id"]

    # Create
    create_res = client.post(
        "/api/v1/rules",
        json={"name": "Original Name", "event_type": "potential_fatigue", "severity": "low"},
        headers={"X-Factory-Id": str(f1)},
    )
    rule_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["version"] == 1

    # Update
    update_res = client.put(
        f"/api/v1/rules/{rule_id}",
        json={"name": "Updated Name", "severity": "medium", "min_confidence": 0.75},
        headers={"X-Factory-Id": str(f1)},
    )
    assert update_res.status_code == 200
    data = update_res.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["severity"] == "medium"
    assert data["version"] == 2


def test_rule_status_toggle(client: TestClient, tenant_fixture):
    """Verify PATCH /status toggles is_enabled and increments version."""
    f1 = tenant_fixture["factory_id"]

    create_res = client.post(
        "/api/v1/rules",
        json={"name": "Toggle Test Rule", "event_type": "temperature_anomaly", "severity": "high", "is_enabled": True},
        headers={"X-Factory-Id": str(f1)},
    )
    rule_id = create_res.json()["data"]["id"]

    # Disable
    patch_res = client.patch(
        f"/api/v1/rules/{rule_id}/status",
        json={"is_enabled": False},
        headers={"X-Factory-Id": str(f1)},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["is_enabled"] is False
    assert patch_res.json()["data"]["version"] == 2


def test_safe_deletion(client: TestClient, tenant_fixture):
    """Verify DELETE removes the rule safely."""
    f1 = tenant_fixture["factory_id"]

    create_res = client.post(
        "/api/v1/rules",
        json={"name": "To Delete Rule", "event_type": "fall", "severity": "critical"},
        headers={"X-Factory-Id": str(f1)},
    )
    rule_id = create_res.json()["data"]["id"]

    # Delete
    del_res = client.delete(
        f"/api/v1/rules/{rule_id}",
        headers={"X-Factory-Id": str(f1)},
    )
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True

    # Confirm 404
    get_res = client.get(
        f"/api/v1/rules/{rule_id}",
        headers={"X-Factory-Id": str(f1)},
    )
    assert get_res.status_code == 404
