"""
tests/test_auth_endpoints.py
Phase 5 Milestone 1 (S-1) — Human Authentication (/login, /me, /refresh, /logout) tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.main import create_application
from app.models.base import Base
from app.models.enums import FactoryStatus, TokenPurpose, UserStatus
from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User


@pytest.fixture()
def auth_env():
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
            AuthToken.__table__,
        ],
    )
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    f1_id = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
    f2_id = uuid.UUID("bbbbbbbb-0002-0002-0002-000000000002")
    role_admin_id = uuid.uuid4()
    role_sup_id = uuid.uuid4()
    active_user_id = uuid.uuid4()
    invited_user_id = uuid.uuid4()
    disabled_user_id = uuid.uuid4()
    no_member_user_id = uuid.uuid4()

    db = TestingSession()
    db.add_all([
        Factory(id=f1_id, name="Plant 1", slug="plant-1", status=FactoryStatus.ACTIVE),
        Factory(id=f2_id, name="Plant 2", slug="plant-2", status=FactoryStatus.ACTIVE),
        Role(id=role_admin_id, code="factory_admin", name="Factory Admin"),
        Role(id=role_sup_id, code="safety_supervisor", name="Safety Supervisor"),
        User(
            id=active_user_id,
            email="mona@plant1.example",
            password_hash=hash_password("AdminPass123!"),
            full_name="Mona Hassan",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        User(
            id=invited_user_id,
            email="invited@plant1.example",
            password_hash=hash_password("InvitePass123!"),
            full_name="Invited User",
            status=UserStatus.INVITED,
        ),
        User(
            id=disabled_user_id,
            email="disabled@plant1.example",
            password_hash=hash_password("DisabledPass123!"),
            full_name="Disabled User",
            status=UserStatus.DISABLED,
            activated_at=datetime.now(timezone.utc),
        ),
        User(
            id=no_member_user_id,
            email="nomember@plant1.example",
            password_hash=hash_password("NoMember123!"),
            full_name="No Membership",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        ),
        FactoryMembership(
            factory_id=f1_id,
            user_id=active_user_id,
            role_id=role_admin_id,
            is_active=True,
        ),
        FactoryMembership(
            factory_id=f2_id,
            user_id=active_user_id,
            role_id=role_sup_id,
            is_active=True,
        ),
    ])
    db.commit()
    db.close()

    app = create_application()

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
    client = TestClient(app)
    return {
        "client": client,
        "Session": TestingSession,
        "f1_id": f1_id,
        "f2_id": f2_id,
        "active_user_id": active_user_id,
    }


class TestLoginEndpoint:
    def test_valid_login_returns_tokens_and_stores_refresh_hash(self, auth_env):
        client = auth_env["client"]
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "Mona@plant1.example", "password": "AdminPass123!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        data = body["data"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 43200
        assert data["user"]["role"] == "factory_admin"
        assert data["user"]["factory_id"] == str(auth_env["f1_id"])

        claims = decode_access_token(data["access_token"])
        assert claims["sub"] == str(auth_env["active_user_id"])
        assert claims["factory_id"] == str(auth_env["f1_id"])
        assert claims["role"] == "factory_admin"

        db = auth_env["Session"]()
        row = db.execute(
            select(AuthToken).where(
                AuthToken.token_hash == hash_refresh_token(data["refresh_token"])
            )
        ).scalar_one_or_none()
        assert row is not None
        assert row.purpose == TokenPurpose.REFRESH
        assert row.token_hash != data["refresh_token"]
        db.close()

    def test_multiple_factory_memberships_select_explicit_factory(self, auth_env):
        client = auth_env["client"]
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "mona@plant1.example",
                "password": "AdminPass123!",
                "factory_id": str(auth_env["f2_id"]),
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user"]["factory_id"] == str(auth_env["f2_id"])
        assert data["user"]["role"] == "safety_supervisor"

    def test_wrong_password_increments_and_locks_account(self, auth_env):
        client = auth_env["client"]
        for _ in range(5):
            r = client.post(
                "/api/v1/auth/login",
                json={"email": "mona@plant1.example", "password": "WrongPassword"},
            )
            assert r.status_code == 401
            assert r.json()["error_code"] == "INVALID_CREDENTIALS"

        locked = client.post(
            "/api/v1/auth/login",
            json={"email": "mona@plant1.example", "password": "AdminPass123!"},
        )
        assert locked.status_code == 403
        assert locked.json()["error_code"] == "ACCOUNT_LOCKED"

    def test_invited_and_disabled_users_rejected(self, auth_env):
        client = auth_env["client"]
        for email, pwd in (
            ("invited@plant1.example", "InvitePass123!"),
            ("disabled@plant1.example", "DisabledPass123!"),
        ):
            resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
            assert resp.status_code == 403
            assert resp.json()["error_code"] == "USER_INACTIVE"

    def test_missing_factory_membership_rejected(self, auth_env):
        client = auth_env["client"]
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nomember@plant1.example", "password": "NoMember123!"},
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "NOT_A_MEMBER"


class TestMeEndpoint:
    def test_me_valid_jwt(self, auth_env):
        client = auth_env["client"]
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "mona@plant1.example", "password": "AdminPass123!"},
        )
        token = login_resp.json()["data"]["access_token"]

        me_resp = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Factory-Id": str(auth_env["f1_id"]),
            },
        )
        assert me_resp.status_code == 200
        me = me_resp.json()["data"]
        assert me["user_id"] == str(auth_env["active_user_id"])
        assert me["factory_id"] == str(auth_env["f1_id"])
        assert me["role"] == "factory_admin"

    def test_me_rejects_expired_tampered_and_mismatched_factory(self, auth_env):
        client = auth_env["client"]
        expired = create_access_token(
            data={"sub": str(auth_env["active_user_id"]), "factory_id": str(auth_env["f1_id"])},
            expires_delta=timedelta(seconds=-10),
        )
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
        assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.jwt.tok"}).status_code == 401

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "mona@plant1.example", "password": "AdminPass123!"},
        )
        token = login_resp.json()["data"]["access_token"]
        mismatch = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Factory-Id": str(auth_env["f2_id"]),
            },
        )
        assert mismatch.status_code == 403


class TestRefreshAndLogout:
    def test_refresh_rotation_and_replay_protection(self, auth_env):
        client = auth_env["client"]
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "mona@plant1.example", "password": "AdminPass123!"},
        )
        refresh_1 = login_resp.json()["data"]["refresh_token"]

        # First refresh rotates token cleanly
        rot_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_1})
        assert rot_resp.status_code == 200
        refresh_2 = rot_resp.json()["data"]["refresh_token"]
        assert refresh_2 != refresh_1

        # Replaying refresh_1 must fail AND revoke refresh_2
        replay = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_1})
        assert replay.status_code == 401
        assert replay.json()["error_code"] == "TOKEN_REPLAYED"

        after_replay = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_2})
        assert after_replay.status_code == 401
        assert after_replay.json()["error_code"] == "TOKEN_REVOKED"

    def test_logout_revokes_refresh_token(self, auth_env):
        client = auth_env["client"]
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "mona@plant1.example", "password": "AdminPass123!"},
        )
        refresh_tok = login_resp.json()["data"]["refresh_token"]

        out = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_tok})
        assert out.status_code == 200
        assert out.json()["data"]["revoked"] is True

        ref_after = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert ref_after.status_code == 401
        assert ref_after.json()["error_code"] == "TOKEN_REVOKED"

    def test_expired_refresh_token_rejected(self, auth_env):
        db = auth_env["Session"]()
        raw_tok = "expired_refresh_token_value_1234567890"
        db.add(
            AuthToken(
                user_id=auth_env["active_user_id"],
                purpose=TokenPurpose.REFRESH,
                token_hash=hash_refresh_token(raw_tok),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        db.commit()
        db.close()

        resp = auth_env["client"].post("/api/v1/auth/refresh", json={"refresh_token": raw_tok})
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "TOKEN_EXPIRED"


class TestPasswordHashing:
    def test_password_within_and_at_72_byte_limit(self):
        normal_hash = hash_password("AdminPass123!")
        assert verify_password("AdminPass123!", normal_hash) is True
        assert verify_password("WrongPass", normal_hash) is False

        exact_72 = "a" * 72
        exact_hash = hash_password(exact_72)
        assert verify_password(exact_72, exact_hash) is True

    def test_password_exceeding_72_bytes_and_multibyte_utf8_rejected(self):
        over_72 = "a" * 73
        with pytest.raises(ValueError, match="72-byte"):
            hash_password(over_72)
        assert verify_password(over_72, hash_password("a" * 72)) is False

        # 40 chars of 'é' = 80 UTF-8 bytes (< 72 chars, > 72 bytes)
        multibyte = "é" * 40
        assert len(multibyte) < 72
        assert len(multibyte.encode("utf-8")) == 80
        with pytest.raises(ValueError, match="72-byte"):
            hash_password(multibyte)
        assert verify_password(multibyte, "$2b$12$fakehash") is False
        assert verify_password("pass", "not-a-valid-bcrypt-hash") is False
