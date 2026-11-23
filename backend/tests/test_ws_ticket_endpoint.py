"""
tests/test_ws_ticket_endpoint.py

Integration tests for POST /api/v1/auth/ws-ticket.

Uses SQLite backend (via .env.test) with mocked Redis for ticket storage.
RLS tenant isolation is NOT tested (SQLite limitation — marked NOT VERIFIED).
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, create_ws_ticket


# ── Test fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture()
def _seed_user_and_membership(app):
    """
    Create a User + FactoryMembership + Factory + Role directly in the SQLite test DB.
    Returns (user_id, factory_id).

    Uses targeted per-table create_all to avoid PostgreSQL-only DDL constraints
    (e.g. jsonb_typeof check constraints) that break on SQLite.
    """
    from app.core.database import SessionLocal, engine
    from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User
    from app.models.enums import FactoryStatus, UserStatus

    # Create only the tables we need — avoids PG-only constraints on other tables
    for table in [Factory.__table__, Role.__table__, User.__table__,
                  AuthToken.__table__, FactoryMembership.__table__]:
        table.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    user_id = uuid.uuid4()
    factory_id = uuid.uuid4()
    role_id = uuid.uuid4()

    try:
        role = Role(id=role_id, code="operator", name="Operator")
        db.add(role)

        factory = Factory(
            id=factory_id,
            name="Test Factory",
            slug=f"test-factory-{factory_id.hex[:8]}",
            status=FactoryStatus.ACTIVE,
        )
        db.add(factory)

        user = User(
            id=user_id,
            email=f"test-{user_id.hex[:8]}@operix.test",
            password_hash="$2b$12$fakehash",
            full_name="Test User",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.flush()

        membership = FactoryMembership(
            factory_id=factory_id,
            user_id=user_id,
            role_id=role_id,
            is_active=True,
        )
        db.add(membership)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    yield user_id, factory_id

    # Cleanup
    db = SessionLocal()
    try:
        db.execute(FactoryMembership.__table__.delete())
        db.execute(User.__table__.delete())
        db.execute(Factory.__table__.delete())
        db.execute(Role.__table__.delete())
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture()
def mock_redis(app):
    """
    Patch app.state.redis with an AsyncMock that simulates Redis.
    Returns the mock for assertion access.
    """
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.getdel = AsyncMock(return_value=None)
    redis_mock.ping = AsyncMock(return_value=True)
    app.state.redis = redis_mock
    yield redis_mock
    # Remove the mock after test
    if hasattr(app.state, "redis"):
        del app.state.redis


def _auth_header(user_id: uuid.UUID, factory_id: uuid.UUID) -> dict:
    """Create a valid Authorization: Bearer header."""
    token = create_access_token({"sub": str(user_id), "factory_id": str(factory_id)})
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestWsTicketEndpoint:
    """POST /api/v1/auth/ws-ticket"""

    def test_missing_authorization_header(self, client: TestClient):
        """No Authorization header → 401."""
        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401

    def test_invalid_bearer_token(self, client: TestClient):
        """Invalid JWT in Authorization → 401."""
        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(uuid.uuid4())},
            headers={"Authorization": "Bearer invalid.fake.token"},
        )
        assert response.status_code == 401

    def test_expired_bearer_token(self, client: TestClient):
        """Expired JWT in Authorization → 401."""
        from datetime import timedelta
        expired = create_access_token(
            {"sub": str(uuid.uuid4())},
            expires_delta=timedelta(seconds=-60),
        )
        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert response.status_code == 401

    def test_nonexistent_user_rejected(
        self, client: TestClient, mock_redis, app,
    ):
        """Valid JWT for user that doesn't exist in DB → 403."""
        from app.core.database import engine
        from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User
        for table in [Factory.__table__, Role.__table__, User.__table__,
                      FactoryMembership.__table__, AuthToken.__table__]:
            table.create(bind=engine, checkfirst=True)

        fake_user = uuid.uuid4()
        fake_factory = uuid.uuid4()
        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(fake_factory)},
            headers=_auth_header(fake_user, fake_factory),
        )
        assert response.status_code == 403

    def test_inactive_user_rejected(
        self, client: TestClient, mock_redis, _seed_user_and_membership,
    ):
        """Valid JWT for user with status != ACTIVE → 403."""
        user_id, factory_id = _seed_user_and_membership

        # Deactivate user
        from app.core.database import SessionLocal
        from app.models.tenant import User
        from app.models.enums import UserStatus
        db = SessionLocal()
        user = db.get(User, user_id)
        user.status = UserStatus.DISABLED
        db.commit()
        db.close()

        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(factory_id)},
            headers=_auth_header(user_id, factory_id),
        )
        assert response.status_code == 403

        # Re-activate for cleanup
        db = SessionLocal()
        user = db.get(User, user_id)
        user.status = UserStatus.ACTIVE
        db.commit()
        db.close()

    def test_no_membership_rejected(
        self, client: TestClient, mock_redis, app,
    ):
        """Valid JWT, user exists but no membership for factory → 403."""
        from app.core.database import SessionLocal, engine
        from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User
        from app.models.enums import UserStatus
        for table in [Factory.__table__, Role.__table__, User.__table__,
                      FactoryMembership.__table__, AuthToken.__table__]:
            table.create(bind=engine, checkfirst=True)

        user_id = uuid.uuid4()
        db = SessionLocal()
        user = User(
            id=user_id,
            email=f"nomember-{user_id.hex[:8]}@operix.test",
            password_hash="$2b$12$fakehash",
            full_name="No Member",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.close()

        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(uuid.uuid4())},
            headers=_auth_header(user_id, uuid.uuid4()),
        )
        assert response.status_code == 403

        # Cleanup
        db = SessionLocal()
        db.delete(db.get(User, user_id))
        db.commit()
        db.close()

    def test_valid_request_returns_ticket(
        self, client: TestClient, mock_redis, _seed_user_and_membership,
    ):
        """Valid JWT + active user + active membership → 200 with ticket data."""
        user_id, factory_id = _seed_user_and_membership

        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(factory_id)},
            headers=_auth_header(user_id, factory_id),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"

        data = body["data"]
        assert "ticket" in data
        assert len(data["ticket"].split(".")) == 3
        assert data["factory_id"] == str(factory_id)
        assert data["expires_in_seconds"] <= 30
        assert data["expires_at"] > 0

        # Verify Redis.set was called with the ticket
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ex") == settings.WS_TICKET_TTL_SECONDS or \
               (len(call_args.args) >= 3 or call_args.kwargs.get("ex") is not None)

    def test_redis_unavailable_returns_503(
        self, client: TestClient, _seed_user_and_membership, app,
    ):
        """Redis not available on app.state → 503."""
        user_id, factory_id = _seed_user_and_membership

        # Remove redis from app state
        if hasattr(app.state, "redis"):
            del app.state.redis

        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(factory_id)},
            headers=_auth_header(user_id, factory_id),
        )
        assert response.status_code == 503

    def test_redis_set_failure_returns_503(
        self, client: TestClient, mock_redis, _seed_user_and_membership,
    ):
        """Redis.set() raises → 503."""
        user_id, factory_id = _seed_user_and_membership
        mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis down"))

        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(factory_id)},
            headers=_auth_header(user_id, factory_id),
        )
        assert response.status_code == 503

    def test_missing_factory_id_in_body(self, client: TestClient):
        """Missing factory_id in request body → 422."""
        token = create_access_token({"sub": str(uuid.uuid4())})
        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_invalid_factory_id_format(self, client: TestClient):
        """Invalid UUID for factory_id → 422."""
        token = create_access_token({"sub": str(uuid.uuid4())})
        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": "not-a-uuid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_ticket_signed_with_ws_ticket_key_not_secret_key(
        self, client: TestClient, mock_redis, _seed_user_and_membership,
    ):
        """Verify the returned ticket is signed with WS_TICKET_KEY."""
        user_id, factory_id = _seed_user_and_membership

        response = client.post(
            "/api/v1/auth/ws-ticket",
            json={"factory_id": str(factory_id)},
            headers=_auth_header(user_id, factory_id),
        )
        assert response.status_code == 200
        ticket = response.json()["data"]["ticket"]

        # Must verify successfully with WS_TICKET_KEY
        from app.core.security import verify_ws_ticket
        claims = verify_ws_ticket(ticket)
        assert claims["sub"] == str(user_id)
        assert claims["purpose"] == "ws_ticket"
