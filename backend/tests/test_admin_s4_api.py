"""
tests/test_admin_s4_api.py
Phase 5 Milestone 4 (S-4) — Users, Roles & Factory Settings API tests.
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
from app.core.database import get_db
from app.main import create_application
from app.models.base import Base
from app.models.enums import FactoryStatus, UserStatus
from app.models.tenant import (
    AuthToken,
    Factory,
    FactoryMembership,
    Permission,
    Role,
    RolePermission,
    User,
)


@pytest.fixture()
def admin_env():
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
            Permission.__table__,
            RolePermission.__table__,
            User.__table__,
            FactoryMembership.__table__,
            AuthToken.__table__,
        ],
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    f1_id = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
    f2_id = uuid.UUID("bbbbbbbb-0002-0002-0002-000000000002")
    admin_id = uuid.uuid4()
    sup_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    role_admin_id = uuid.uuid4()
    role_sup_id = uuid.uuid4()
    role_op_id = uuid.uuid4()
    perm_id = uuid.uuid4()

    db = TestingSession()
    db.add_all([
        Factory(id=f1_id, name="Plant 1", slug="plant-1", status=FactoryStatus.ACTIVE, timezone="UTC", evidence_retention_days=30),
        Factory(id=f2_id, name="Plant 2", slug="plant-2", status=FactoryStatus.ACTIVE, timezone="UTC", evidence_retention_days=60),
        Role(id=role_admin_id, code="factory_admin", name="Factory Admin"),
        Role(id=role_sup_id, code="safety_supervisor", name="Safety Supervisor"),
        Role(id=role_op_id, code="operator", name="Operator"),
        Permission(id=perm_id, code="incidents:acknowledge", description="Acknowledge incidents"),
        RolePermission(role_id=role_sup_id, permission_id=perm_id),
        User(
            id=admin_id,
            email="admin@plant1.example",
            password_hash="$2b$12$secret_hash",
            full_name="Admin User",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        User(
            id=sup_id,
            email="sup@plant1.example",
            password_hash="$2b$12$secret_hash2",
            full_name="Sup User",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        User(
            id=other_user_id,
            email="other@plant2.example",
            password_hash="$2b$12$secret_hash3",
            full_name="Other Factory User",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        FactoryMembership(factory_id=f1_id, user_id=admin_id, role_id=role_admin_id, is_active=True),
        FactoryMembership(factory_id=f1_id, user_id=sup_id, role_id=role_sup_id, is_active=True),
        FactoryMembership(factory_id=f2_id, user_id=other_user_id, role_id=role_admin_id, is_active=True),
    ])
    db.commit()
    db.close()

    app = create_application()
    admin_user = AuthenticatedUser(user_id=admin_id, factory_id=f1_id, role="factory_admin", full_name="Admin User")
    operator_user = AuthenticatedUser(user_id=uuid.uuid4(), factory_id=f1_id, role="operator", full_name="Operator")

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
    app.dependency_overrides[get_current_user_context] = lambda: admin_user
    client = TestClient(app)
    return {
        "app": app,
        "client": client,
        "f1_id": f1_id,
        "sup_id": sup_id,
        "other_user_id": other_user_id,
        "role_sup_id": role_sup_id,
        "operator_user": operator_user,
    }


class TestAdminS4API:
    def test_users_list_invite_update_and_sensitive_field_exclusion(self, admin_env):
        client = admin_env["client"]
        resp = client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        for item in data["items"]:
            assert "password_hash" not in item
            assert "failed_login_count" not in item
            assert "locked_until" not in item

        # Cross-factory user denied (404)
        assert client.get(f"/api/v1/users/{admin_env['other_user_id']}").status_code == 404

        # Invite new user
        inv = client.post(
            "/api/v1/users/invite",
            json={"email": "new.worker@plant1.example", "full_name": "New Worker", "role_code": "operator"},
        )
        assert inv.status_code == 201
        inv_data = inv.json()["data"]
        assert inv_data["status"] == "invited"
        assert inv_data["role_code"] == "operator"
        assert "password_hash" not in inv_data

        # Activate user via PATCH
        upd = client.patch(
            f"/api/v1/users/{inv_data['user_id']}",
            json={"status": "active", "full_name": "Activated Worker"},
        )
        assert upd.status_code == 200
        assert upd.json()["data"]["status"] == "active"
        assert upd.json()["data"]["activated_at"] is not None

    def test_roles_permissions_and_membership_assignment(self, admin_env):
        client = admin_env["client"]
        roles = client.get("/api/v1/roles").json()["data"]
        assert roles["total"] == 3

        role_detail = client.get(f"/api/v1/roles/{admin_env['role_sup_id']}").json()["data"]
        assert role_detail["permissions"][0]["code"] == "incidents:acknowledge"

        perms = client.get("/api/v1/roles/permissions").json()["data"]
        assert len(perms) == 1

        assigned = client.patch(
            f"/api/v1/roles/memberships/{admin_env['sup_id']}",
            json={"role_code": "operator"},
        )
        assert assigned.status_code == 200
        assert assigned.json()["data"]["role_code"] == "operator"

    def test_factory_settings_and_rbac_enforcement(self, admin_env):
        app = admin_env["app"]
        client = admin_env["client"]

        cur = client.get("/api/v1/factories/current")
        assert cur.status_code == 200
        assert cur.json()["data"]["evidence_retention_days"] == 30

        upd = client.patch(
            "/api/v1/factories/current",
            json={"timezone": "Africa/Cairo", "evidence_retention_days": 90},
        )
        assert upd.status_code == 200
        assert upd.json()["data"]["timezone"] == "Africa/Cairo"
        assert upd.json()["data"]["evidence_retention_days"] == 90

        # Operator cannot list/invite users, assign roles, or update factory settings
        app.dependency_overrides[get_current_user_context] = lambda: admin_env["operator_user"]
        assert client.get("/api/v1/users").status_code == 403
        assert client.post(
            "/api/v1/users/invite",
            json={"email": "x@y.com", "full_name": "X", "role_code": "operator"},
        ).status_code == 403
        assert client.patch(
            f"/api/v1/roles/memberships/{admin_env['sup_id']}",
            json={"role_code": "factory_admin"},
        ).status_code == 403
        assert client.patch("/api/v1/factories/current", json={"name": "Hacked"}).status_code == 403
        # Operator can still read current factory info
        assert client.get("/api/v1/factories/current").status_code == 200

    def test_role_assignment_hierarchy_and_service_layer_enforcement(self, admin_env):
        from app.core.security import AuthorizationException
        from app.models.tenant import Role
        from app.schemas.admin import UserInviteRequest, UserUpdateRequest
        from app.services.admin_service import AdminService

        app = admin_env["app"]
        client = admin_env["client"]
        f1_id = admin_env["f1_id"]
        sup_id = admin_env["sup_id"]

        # Seed factory_manager and platform_admin roles in DB
        db_gen = app.dependency_overrides[get_db]
        db = next(db_gen())
        db.add_all([
            Role(id=uuid.uuid4(), code="factory_manager", name="Factory Manager"),
            Role(id=uuid.uuid4(), code="platform_admin", name="Platform Admin"),
        ])
        db.commit()
        db.close()

        # 1. factory_admin can assign factory_manager, but NOT platform_admin
        assert (
            client.patch(f"/api/v1/roles/memberships/{sup_id}", json={"role_code": "factory_manager"}).status_code
            == 200
        )
        pa_denied = client.patch(f"/api/v1/roles/memberships/{sup_id}", json={"role_code": "platform_admin"})
        assert pa_denied.status_code == 403
        assert pa_denied.json()["error_code"] == "INSUFFICIENT_PERMISSIONS"

        # 2. Switch caller to factory_manager
        mgr_user = AuthenticatedUser(
            user_id=uuid.uuid4(),
            factory_id=f1_id,
            role="factory_manager",
            full_name="Factory Manager",
        )
        app.dependency_overrides[get_current_user_context] = lambda: mgr_user

        # factory_manager assigning factory_admin or platform_admin -> denied (403)
        for forbidden_role in ("factory_admin", "platform_admin", "factory_manager"):
            r_assign = client.patch(f"/api/v1/roles/memberships/{sup_id}", json={"role_code": forbidden_role})
            assert r_assign.status_code == 403
            assert r_assign.json()["error_code"] == "INSUFFICIENT_PERMISSIONS"

            r_inv = client.post(
                "/api/v1/users/invite",
                json={"email": f"blocked_{forbidden_role}@plant1.example", "full_name": "Blocked", "role_code": forbidden_role},
            )
            assert r_inv.status_code == 403

            r_upd = client.patch(f"/api/v1/users/{sup_id}", json={"role_code": forbidden_role})
            assert r_upd.status_code == 403

        # factory_manager assigning lower-privilege role -> succeeds
        r_ok = client.patch(f"/api/v1/roles/memberships/{sup_id}", json={"role_code": "safety_supervisor"})
        assert r_ok.status_code == 200
        assert r_ok.json()["data"]["role_code"] == "safety_supervisor"

        # 3. Direct service-layer calls cannot bypass hierarchy
        db = next(db_gen())
        try:
            with pytest.raises(AuthorizationException):
                AdminService.invite_user(
                    db,
                    f1_id,
                    UserInviteRequest(email="direct@plant1.example", full_name="Direct", role_code="factory_admin"),
                    actor_role="factory_manager",
                )
            with pytest.raises(AuthorizationException):
                AdminService.assign_membership_role(
                    db, f1_id, sup_id, "platform_admin", actor_role="factory_manager"
                )
            with pytest.raises(AuthorizationException):
                AdminService.update_factory_user(
                    db, f1_id, sup_id, UserUpdateRequest(role_code="factory_admin"), actor_role="factory_manager"
                )
        finally:
            db.rollback()
            db.close()
