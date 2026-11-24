"""
tests/test_incidents_api.py
Phase 5 Milestone 2 (S-2) — Incidents Management API tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import AuthenticatedUser, get_current_user_context
from app.core.database import get_db
from app.main import create_application
from app.models.base import Base
from app.models.enums import EventType, FactoryStatus, IncidentState, SeverityLevel, UserStatus
from app.models.incidents import Incident
from app.models.tenant import Factory, FactoryMembership, Role, User


@pytest.fixture()
def incidents_env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Factory.__table__,
            Role.__table__,
            User.__table__,
            FactoryMembership.__table__,
            Incident.__table__,
        ],
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    f1_id = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
    f2_id = uuid.UUID("bbbbbbbb-0002-0002-0002-000000000002")
    sup_id = uuid.uuid4()
    viewer_id = uuid.uuid4()
    role_sup_id = uuid.uuid4()
    role_view_id = uuid.uuid4()
    inc_f1_id = uuid.uuid4()
    inc_f2_id = uuid.uuid4()

    db = TestingSession()
    db.add_all([
        Factory(id=f1_id, name="Plant 1", slug="plant-1", status=FactoryStatus.ACTIVE),
        Factory(id=f2_id, name="Plant 2", slug="plant-2", status=FactoryStatus.ACTIVE),
        Role(id=role_sup_id, code="safety_supervisor", name="Safety Supervisor"),
        Role(id=role_view_id, code="viewer", name="Viewer"),
        User(
            id=sup_id,
            email="sup@plant1.example",
            password_hash="hash",
            full_name="Supervisor",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        User(
            id=viewer_id,
            email="viewer@plant1.example",
            password_hash="hash",
            full_name="Viewer",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        FactoryMembership(factory_id=f1_id, user_id=sup_id, role_id=role_sup_id, is_active=True),
        FactoryMembership(factory_id=f1_id, user_id=viewer_id, role_id=role_view_id, is_active=True),
        Incident(
            id=inc_f1_id,
            factory_id=f1_id,
            incident_type=EventType.PPE_VIOLATION,
            severity=SeverityLevel.HIGH,
            state=IncidentState.DETECTED,
        ),
        Incident(
            id=inc_f2_id,
            factory_id=f2_id,
            incident_type=EventType.FALL,
            severity=SeverityLevel.CRITICAL,
            state=IncidentState.DETECTED,
        ),
    ])
    db.commit()
    db.close()

    app = create_application()
    sup_user = AuthenticatedUser(user_id=sup_id, factory_id=f1_id, role="safety_supervisor", full_name="Supervisor")
    viewer_user = AuthenticatedUser(user_id=viewer_id, factory_id=f1_id, role="viewer", full_name="Viewer")

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
        "sup_user": sup_user,
        "viewer_user": viewer_user,
        "inc_f1_id": inc_f1_id,
        "inc_f2_id": inc_f2_id,
    }


class TestIncidentsAPI:
    def test_list_and_get_incident_tenant_isolated(self, incidents_env):
        client = incidents_env["client"]
        resp = client.get("/api/v1/incidents")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(incidents_env["inc_f1_id"])

        # Cross-factory incident must not be visible
        cross = client.get(f"/api/v1/incidents/{incidents_env['inc_f2_id']}")
        assert cross.status_code == 404

    def test_acknowledge_resolve_and_invalid_transitions(self, incidents_env):
        client = incidents_env["client"]
        inc_id = incidents_env["inc_f1_id"]

        with patch("app.services.incident_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            ack = client.patch(f"/api/v1/incidents/{inc_id}/acknowledge")
            assert ack.status_code == 200
            assert ack.json()["data"]["state"] == "under_review"
            assert mock_ws.await_count == 1

            res = client.patch(
                f"/api/v1/incidents/{inc_id}/resolve",
                json={"resolution_note": "Worker equipped helmet."},
            )
            assert res.status_code == 200
            res_data = res.json()["data"]
            assert res_data["state"] == "resolved"
            assert res_data["resolved_at"] is not None
            assert res_data["resolution_note"] == "Worker equipped helmet."
            assert mock_ws.await_count == 2

            # Cannot acknowledge or resolve an already resolved incident
            ack_again = client.patch(f"/api/v1/incidents/{inc_id}/acknowledge")
            assert ack_again.status_code == 400
            assert ack_again.json()["error_code"] == "INVALID_STATE_TRANSITION"

            res_again = client.patch(f"/api/v1/incidents/{inc_id}/resolve")
            assert res_again.status_code == 400
            assert res_again.json()["error_code"] == "INVALID_STATE_TRANSITION"
            assert mock_ws.await_count == 2

    def test_viewer_cannot_modify_incidents(self, incidents_env):
        app = incidents_env["app"]
        client = incidents_env["client"]
        app.dependency_overrides[get_current_user_context] = lambda: incidents_env["viewer_user"]

        assert client.get("/api/v1/incidents").status_code == 200
        assert client.post(
            "/api/v1/incidents",
            json={"incident_type": "ppe_violation", "severity": "low"},
        ).status_code == 403
        assert client.patch(f"/api/v1/incidents/{incidents_env['inc_f1_id']}/acknowledge").status_code == 403
        assert client.patch(f"/api/v1/incidents/{incidents_env['inc_f1_id']}/resolve").status_code == 403

    def test_broadcast_not_executed_when_commit_fails(self, incidents_env):
        app = incidents_env["app"]
        TestingSession = incidents_env["Session"]

        def _failing_commit_db():
            session = TestingSession()
            session.commit = lambda: (_ for _ in ()).throw(RuntimeError("Simulated DB commit failure"))
            try:
                yield session
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        app.dependency_overrides[get_db] = _failing_commit_db
        failing_client = TestClient(app)

        with patch("app.services.incident_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            with pytest.raises(RuntimeError, match="Simulated DB commit failure"):
                failing_client.patch(f"/api/v1/incidents/{incidents_env['inc_f1_id']}/acknowledge")
            assert mock_ws.await_count == 0
