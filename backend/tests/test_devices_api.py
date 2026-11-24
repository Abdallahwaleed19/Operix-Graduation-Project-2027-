"""
tests/test_devices_api.py
Phase 5 Milestone 3 (S-3) — Cameras & Sensors API tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import AuthenticatedUser, get_current_user_context
from app.core.config import settings
from app.core.database import get_db
from app.main import create_application
from app.models.base import Base
from app.models.enums import CameraType, FactoryStatus, SensorType, SourceStatus
from app.models.operational import Camera, Department, Sensor, SensorReading
from app.models.tenant import Factory


@pytest.fixture()
def devices_env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Factory.__table__,
            Department.__table__,
            Camera.__table__,
            Sensor.__table__,
            SensorReading.__table__,
        ],
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    f1_id = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
    f2_id = uuid.UUID("bbbbbbbb-0002-0002-0002-000000000002")
    dept_f1_id = uuid.uuid4()
    cam_f2_id = uuid.uuid4()
    sensor_f2_id = uuid.uuid4()
    sup_id = uuid.uuid4()

    db = TestingSession()
    db.add_all([
        Factory(id=f1_id, name="Plant 1", slug="plant-1", status=FactoryStatus.ACTIVE),
        Factory(id=f2_id, name="Plant 2", slug="plant-2", status=FactoryStatus.ACTIVE),
        Department(id=dept_f1_id, factory_id=f1_id, name="Welding"),
        Camera(
            id=cam_f2_id,
            factory_id=f2_id,
            name="Other Plant Cam",
            camera_type=CameraType.CCTV,
            stream_url_ref="rtsp://other/cam1",
            status=SourceStatus.AVAILABLE,
            is_active=True,
        ),
        Sensor(
            id=sensor_f2_id,
            factory_id=f2_id,
            name="Other Plant Temp",
            sensor_type=SensorType.TEMPERATURE,
            unit="C",
            sampling_interval_s=30,
            device_key_hash="secret_hash_should_never_leak",
            status=SourceStatus.AVAILABLE,
            is_active=True,
        ),
    ])
    db.commit()
    db.close()

    app = create_application()
    sup_user = AuthenticatedUser(user_id=sup_id, factory_id=f1_id, role="safety_supervisor", full_name="Supervisor")
    viewer_user = AuthenticatedUser(user_id=uuid.uuid4(), factory_id=f1_id, role="viewer", full_name="Viewer")

    def _override_db():
        session = TestingSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user_context] = lambda: sup_user
    client = TestClient(app)
    return {
        "app": app,
        "client": client,
        "Session": TestingSession,
        "f1_id": f1_id,
        "f2_id": f2_id,
        "dept_f1_id": dept_f1_id,
        "cam_f2_id": cam_f2_id,
        "sensor_f2_id": sensor_f2_id,
        "viewer_user": viewer_user,
    }


class TestCamerasAndSensorsAPI:
    def test_camera_crud_toggle_and_tenant_isolation(self, devices_env):
        client = devices_env["client"]
        create_resp = client.post(
            "/api/v1/devices/cameras",
            json={
                "name": "Gate Cam 1",
                "camera_type": "cctv",
                "department_id": str(devices_env["dept_f1_id"]),
                "location_label": "North Gate",
                "stream_url_ref": "rtsp://internal/gate1",
            },
        )
        assert create_resp.status_code == 201
        cam = create_resp.json()["data"]
        cam_id = cam["id"]
        assert cam["is_active"] is True

        # List excludes factory 2 camera
        listed = client.get("/api/v1/devices/cameras").json()["data"]
        assert listed["total"] == 1
        assert listed["items"][0]["id"] == cam_id

        # Cross-factory camera denied (404)
        assert client.get(f"/api/v1/devices/cameras/{devices_env['cam_f2_id']}").status_code == 404

        # Update + toggle
        upd = client.patch(f"/api/v1/devices/cameras/{cam_id}", json={"location_label": "South Gate"})
        assert upd.status_code == 200
        assert upd.json()["data"]["location_label"] == "South Gate"

        tog = client.post(f"/api/v1/devices/cameras/{cam_id}/toggle")
        assert tog.status_code == 200
        assert tog.json()["data"]["is_active"] is False
        assert tog.json()["data"]["status"] == "unavailable"

    def test_sensor_crud_readings_and_secret_exclusion(self, devices_env):
        client = devices_env["client"]
        create_resp = client.post(
            "/api/v1/devices/sensors",
            json={
                "name": "Furnace Temp 1",
                "sensor_type": "temperature",
                "unit": "C",
                "sampling_interval_s": 15,
            },
        )
        assert create_resp.status_code == 201
        sensor = create_resp.json()["data"]
        sensor_id = sensor["id"]
        assert "device_key_hash" not in sensor

        # Seed a reading and query /readings
        db = devices_env["Session"]()
        db.add(
            SensorReading(
                sensor_id=uuid.UUID(sensor_id),
                recorded_at=datetime.now(timezone.utc),
                factory_id=devices_env["f1_id"],
                value=72.5,
            )
        )
        db.commit()
        db.close()

        readings = client.get(f"/api/v1/devices/sensors/{sensor_id}/readings")
        assert readings.status_code == 200
        assert readings.json()["data"]["total"] == 1
        assert readings.json()["data"]["items"][0]["value"] == 72.5

        # Cross-factory sensor rejected
        assert client.get(f"/api/v1/devices/sensors/{devices_env['sensor_f2_id']}").status_code == 404

        # Toggle
        tog = client.post(f"/api/v1/devices/sensors/{sensor_id}/toggle")
        assert tog.status_code == 200
        assert tog.json()["data"]["is_active"] is False

    def test_viewer_rbac_and_cv_producer_auth_preserved(self, devices_env):
        app = devices_env["app"]
        client = devices_env["client"]
        app.dependency_overrides[get_current_user_context] = lambda: devices_env["viewer_user"]

        assert client.get("/api/v1/devices/cameras").status_code == 200
        assert client.post(
            "/api/v1/devices/cameras",
            json={"name": "Blocked Cam", "stream_url_ref": "rtsp://x"},
        ).status_code == 403
        assert client.post(
            "/api/v1/devices/sensors",
            json={"name": "Blocked Sensor"},
        ).status_code == 403

        # Existing CV ingestion auth still rejects missing X-Camera-Key with 401
        cv_resp = client.post("/api/v1/events/ingest", json={})
        assert cv_resp.status_code == 401

    def test_camera_response_masks_embedded_rtsp_credentials(self, devices_env):
        from app.schemas.devices import CameraResponse

        client = devices_env["client"]
        resp = client.post(
            "/api/v1/devices/cameras",
            json={
                "name": "Cred Mask Cam",
                "camera_type": "cctv",
                "stream_url_ref": "rtsp://camuser:p@ss@word@10.0.0.15:554/live",
            },
        )
        assert resp.status_code == 201
        returned_ref = resp.json()["data"]["stream_url_ref"]
        assert "p@ss@word" not in returned_ref
        assert returned_ref == "rtsp://***:***@10.0.0.15:554/live"

        # Verify unit edge cases: encoded creds, multiple @, IPv6, vault/plain refs, query-string @
        assert CameraResponse._mask_embedded_credentials("rtsp://admin:p%40ss@10.0.0.5/live") == "rtsp://***:***@10.0.0.5/live"
        assert CameraResponse._mask_embedded_credentials("rtsp://user:p@ss@[::1]:554/stream") == "rtsp://***:***@[::1]:554/stream"
        assert CameraResponse._mask_embedded_credentials("rtsp://[::1]:554/stream") == "rtsp://[::1]:554/stream"
        assert CameraResponse._mask_embedded_credentials("rtsp://10.0.0.5/live?tag=a@b") == "rtsp://10.0.0.5/live?tag=a@b"
        assert CameraResponse._mask_embedded_credentials("vault://secrets/cam1") == "vault://secrets/cam1"
        assert CameraResponse._mask_embedded_credentials("cam_ref_01") == "cam_ref_01"
