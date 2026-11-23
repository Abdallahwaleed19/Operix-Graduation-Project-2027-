"""
tests/test_ws_ticket_auth.py

Integration tests for the /ws/v2/events WebSocket endpoint (ticket auth).

Tests verify pre-accept rejection for invalid/expired/replayed tickets,
successful authenticated connection with handshake, and membership revocation.

Uses SQLite backend + mocked Redis. RLS is NOT VERIFIED (SQLite limitation).
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import (
    _build_token,
    create_access_token,
    create_ws_ticket,
    get_ws_ticket_redis_key,
    verify_ws_ticket,
)


# ── Shared fixtures ──────────────────────────────────────────────────────────

_ROLE_ID = uuid.uuid4()


@pytest.fixture()
def _seed_db(app):
    """
    Seed SQLite test DB with User + Factory + Role + FactoryMembership.
    Returns (user_id, factory_id).
    """
    from app.core.database import SessionLocal, engine
    from app.models.enums import FactoryStatus, UserStatus
    from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User

    # Create only the needed tables to avoid PG-only DDL constraints on SQLite
    for table in [Factory.__table__, Role.__table__, User.__table__,
                  AuthToken.__table__, FactoryMembership.__table__]:
        table.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    user_id = uuid.uuid4()
    factory_id = uuid.uuid4()

    try:
        role = Role(id=_ROLE_ID, code=f"op-{_ROLE_ID.hex[:8]}", name="Operator")
        db.merge(role)
        db.flush()

        factory = Factory(
            id=factory_id,
            name="WS Test Factory",
            slug=f"ws-test-{factory_id.hex[:8]}",
            status=FactoryStatus.ACTIVE,
        )
        db.add(factory)

        user = User(
            id=user_id,
            email=f"ws-{user_id.hex[:8]}@operix.test",
            password_hash="$2b$12$fakehash",
            full_name="WS Test User",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.flush()

        membership = FactoryMembership(
            factory_id=factory_id,
            user_id=user_id,
            role_id=_ROLE_ID,
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


def _make_valid_ticket_and_redis(user_id, factory_id, mock_redis):
    """
    Create a valid WS ticket and configure mock_redis to return it on getdel.
    Returns the ticket string.
    """
    ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)
    ticket_bytes = ticket.encode("utf-8")

    # Configure getdel to return the ticket bytes once, then None (replay)
    mock_redis.getdel = AsyncMock(side_effect=[ticket_bytes, None])
    return ticket


@pytest.fixture()
def mock_redis(app):
    """Inject a mock Redis into app.state."""
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.getdel = AsyncMock(return_value=None)
    redis_mock.ping = AsyncMock(return_value=True)
    app.state.redis = redis_mock
    yield redis_mock
    if hasattr(app.state, "redis"):
        del app.state.redis


# ── Pre-accept rejection tests ───────────────────────────────────────────────

class TestWsTicketPreAcceptRejection:
    """
    All these tests verify that the WebSocket is rejected BEFORE accept().
    With Starlette 1.10 + httpx2, the server uses send_denial_response()
    which raises WebSocketDisconnect in the TestClient.
    """

    def test_no_ticket_rejected(self, client: TestClient):
        """Missing ticket query parameter → rejection."""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/v2/events"):
                pass

    def test_invalid_ticket_signature_rejected(self, client: TestClient, mock_redis):
        """Ticket signed with wrong key → rejection."""
        forged = _build_token(
            {
                "sub": str(uuid.uuid4()),
                "factory_id": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(seconds=30)).timestamp()),
                "purpose": "ws_ticket",
                "iss": "operix",
                "aud": "operix_ws",
            },
            "wrong-key-definitely-not-matching-32b!",
        )
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={forged}"):
                pass

    def test_expired_ticket_rejected(self, client: TestClient, mock_redis):
        """Ticket with exp in the past → rejection."""
        now = datetime.now(timezone.utc)
        expired = _build_token(
            {
                "sub": str(uuid.uuid4()),
                "factory_id": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "iat": int((now - timedelta(seconds=60)).timestamp()),
                "exp": int((now - timedelta(seconds=30)).timestamp()),
                "purpose": "ws_ticket",
                "iss": "operix",
                "aud": "operix_ws",
            },
            settings.WS_TICKET_KEY,
        )
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={expired}"):
                pass

    def test_replayed_ticket_rejected(
        self, client: TestClient, mock_redis, _seed_db,
    ):
        """Ticket that Redis.getdel returns None for (already consumed) → rejection."""
        user_id, factory_id = _seed_db
        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)

        # getdel returns None → ticket already consumed
        mock_redis.getdel = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={ticket}"):
                pass

    def test_ticket_mismatch_rejected(
        self, client: TestClient, mock_redis, _seed_db,
    ):
        """Stored ticket in Redis doesn't match presented ticket → rejection."""
        user_id, factory_id = _seed_db
        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)

        # Return different bytes than the actual ticket
        mock_redis.getdel = AsyncMock(return_value=b"different-ticket-bytes-entirely")

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={ticket}"):
                pass

    def test_no_membership_rejected(self, client: TestClient, mock_redis, app):
        """Valid ticket but user has no membership → rejection."""
        from app.core.database import SessionLocal, engine
        from app.models.enums import UserStatus
        from app.models.tenant import AuthToken, Factory, FactoryMembership, Role, User

        for table in [Factory.__table__, Role.__table__, User.__table__,
                      AuthToken.__table__, FactoryMembership.__table__]:
            table.create(bind=engine, checkfirst=True)

        user_id = uuid.uuid4()
        factory_id = uuid.uuid4()

        db = SessionLocal()
        user = User(
            id=user_id,
            email=f"nomem-{user_id.hex[:8]}@operix.test",
            password_hash="$2b$12$fakehash",
            full_name="No Membership",
            status=UserStatus.ACTIVE,
            activated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.close()

        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)
        mock_redis.getdel = AsyncMock(return_value=ticket.encode("utf-8"))

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={ticket}"):
                pass

        # Cleanup
        db = SessionLocal()
        db.delete(db.get(User, user_id))
        db.commit()
        db.close()

    def test_redis_unavailable_rejected(self, client: TestClient, app, _seed_db):
        """Redis not on app.state → rejection."""
        user_id, factory_id = _seed_db
        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)

        # Ensure redis is not set
        if hasattr(app.state, "redis"):
            del app.state.redis

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={ticket}"):
                pass

    def test_redis_getdel_error_rejected(
        self, client: TestClient, mock_redis, _seed_db,
    ):
        """Redis.getdel() raises exception → rejection."""
        user_id, factory_id = _seed_db
        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)

        mock_redis.getdel = AsyncMock(side_effect=ConnectionError("Redis down"))

        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={ticket}"):
                pass


# ── Successful connection tests ──────────────────────────────────────────────

class TestWsTicketSuccessfulConnection:

    def test_valid_ticket_accepted_and_handshake(
        self, client: TestClient, mock_redis, _seed_db,
    ):
        """Valid ticket → accept → receive handshake message."""
        user_id, factory_id = _seed_db
        ticket = _make_valid_ticket_and_redis(user_id, factory_id, mock_redis)

        with client.websocket_connect(f"/ws/v2/events?ticket={ticket}") as ws:
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "connection_established"
            assert msg["factory_id"] == str(factory_id)
            assert msg["user_id"] == str(user_id)
            assert msg["status"] == "connected"
            assert "ticket auth" in msg["message"]
            assert "timestamp" in msg

    def test_ping_pong_on_ticket_ws(
        self, client: TestClient, mock_redis, _seed_db,
    ):
        """Verify ping/pong works on the ticket-auth WebSocket."""
        user_id, factory_id = _seed_db
        ticket = _make_valid_ticket_and_redis(user_id, factory_id, mock_redis)

        with client.websocket_connect(f"/ws/v2/events?ticket={ticket}") as ws:
            _ = ws.receive_text()  # handshake
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            pong = json.loads(response)
            assert pong["type"] == "pong"
            assert "timestamp" in pong

    def test_replay_second_use_rejected(
        self, client: TestClient, mock_redis, _seed_db,
    ):
        """
        First use of ticket succeeds; second use (replay) fails because
        Redis.getdel returns None on the second call.
        """
        user_id, factory_id = _seed_db
        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)
        ticket_bytes = ticket.encode("utf-8")

        # First call returns ticket, second returns None
        mock_redis.getdel = AsyncMock(side_effect=[ticket_bytes, None])

        # First connection succeeds
        with client.websocket_connect(f"/ws/v2/events?ticket={ticket}") as ws:
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "connection_established"

        # Second connection fails (replay)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/v2/events?ticket={ticket}"):
                pass


# ── Legacy endpoint backward compatibility ───────────────────────────────────

class TestLegacyEndpointUnchanged:

    def test_legacy_ws_events_still_works(self, client: TestClient):
        """Verify legacy /ws/events endpoint still accepts human JWT tokens."""
        factory_id = str(uuid.uuid4())
        token = create_access_token({"sub": "legacy_user", "factory_id": factory_id})

        with client.websocket_connect(f"/ws/events?token={token}&factory_id={factory_id}") as ws:
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "connection_established"
            assert msg["factory_id"] == factory_id

    def test_legacy_ws_events_no_token_rejected(self, client: TestClient):
        """Legacy endpoint still rejects connections without token."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/events"):
                pass
        assert exc_info.value.code == 4401
