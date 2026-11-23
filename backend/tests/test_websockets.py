"""
tests/test_websockets.py
Automated tests for real-time WebSocket connection lifecycle, cryptographic authentication,
heartbeat ping-pong, live safety event broadcasting, and strict multi-tenant isolation.
"""
from datetime import datetime, timezone
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.security import create_access_token


def test_websocket_missing_token_rejected(client: TestClient):
    """Verify WebSocket connection without token is rejected with code 4401."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/events"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_invalid_token_rejected(client: TestClient):
    """Verify WebSocket connection with forged/malformed token is rejected with code 4401."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/events?token=invalid.tampered.token"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_expired_token_rejected(client: TestClient):
    """Verify WebSocket connection with expired token is rejected with code 4401."""
    from datetime import timedelta
    factory_id = str(uuid.uuid4())
    expired_token = create_access_token(
        {"sub": "expired_user", "factory_id": factory_id},
        expires_delta=timedelta(seconds=-60),
    )
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/events?token={expired_token}"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_cross_tenant_rejected(client: TestClient):
    """
    Verify cross-tenant attempt:
    Token issued for Factory A, but client specifies Factory B in query parameters.
    Must be rejected with code 4403 (FORBIDDEN).
    """
    factory_a = str(uuid.uuid4())
    factory_b = str(uuid.uuid4())
    token_for_a = create_access_token({"sub": "user_a", "factory_id": factory_a})

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/events?token={token_for_a}&factory_id={factory_b}"):
            pass
    assert exc_info.value.code == 4403


def test_websocket_connection_and_handshake(client: TestClient):
    """Verify authenticated WebSocket connection succeeds and returns initial handshake."""
    factory_id = str(uuid.uuid4())
    token = create_access_token({"sub": "dashboard_user_1", "factory_id": factory_id})

    with client.websocket_connect(f"/ws/events?token={token}&factory_id={factory_id}") as websocket:
        data = websocket.receive_text()
        msg = json.loads(data)
        assert msg["type"] == "connection_established"
        assert msg["factory_id"] == factory_id
        assert msg["user_id"] == "dashboard_user_1"
        assert msg["status"] == "connected"


def test_websocket_ping_pong_heartbeat(client: TestClient):
    """Verify WebSocket responds to client ping messages with pong."""
    factory_id = str(uuid.uuid4())
    token = create_access_token({"sub": "ping_tester", "factory_id": factory_id})

    with client.websocket_connect(f"/ws/events?token={token}") as websocket:
        # Consume initial handshake
        _ = websocket.receive_text()

        # Send ping
        websocket.send_text(json.dumps({"type": "ping"}))
        response = websocket.receive_text()
        pong = json.loads(response)
        assert pong["type"] == "pong"
        assert "timestamp" in pong


def test_websocket_event_broadcast_on_ingestion(client: TestClient):
    """
    Verify that when an event is ingested via authenticated REST API,
    it is immediately broadcast to active WebSocket listeners for that factory.
    """
    factory_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    token = create_access_token({"sub": "dashboard_listener", "factory_id": factory_id})

    with client.websocket_connect(f"/ws/events?token={token}&factory_id={factory_id}") as websocket:
        # Read handshake
        _ = websocket.receive_text()

        # Ingest event for this factory with valid camera key and factory header
        payload = {
            "event_id": event_id,
            "event_type": "ppe_violation",
            "event_state": "started",
            "module": "ppe_detection",
            "camera_id": "camera_01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.92,
            "attributes": {"missing": ["helmet"]},
        }
        res = client.post(
            "/api/v1/events/ingest",
            json=payload,
            headers={
                "X-Camera-Key": settings.DEFAULT_CV_API_KEY,
                "X-Factory-Id": factory_id,
            },
        )
        assert res.status_code == 201

        # WebSocket must receive the broadcast message
        ws_msg_text = websocket.receive_text()
        ws_msg = json.loads(ws_msg_text)
        assert ws_msg["type"] == "safety_event"
        assert ws_msg["factory_id"] == factory_id
        assert ws_msg["data"]["event_id"] == event_id
        assert ws_msg["data"]["event_type"] == "ppe_violation"
        assert ws_msg["data"]["module"] == "ppe_detection"


def test_websocket_tenant_isolation(client: TestClient):
    """
    Verify strict tenant isolation:
    Events ingested for Factory A MUST NOT be broadcast to clients connected to Factory B.
    """
    factory_a = str(uuid.uuid4())
    factory_b = str(uuid.uuid4())
    event_for_a = str(uuid.uuid4())

    token_a = create_access_token({"sub": "operator_a", "factory_id": factory_a})
    token_b = create_access_token({"sub": "operator_b", "factory_id": factory_b})

    with client.websocket_connect(f"/ws/events?token={token_a}&factory_id={factory_a}") as ws_a:
        _ = ws_a.receive_text()  # Handshake A

        with client.websocket_connect(f"/ws/events?token={token_b}&factory_id={factory_b}") as ws_b:
            _ = ws_b.receive_text()  # Handshake B

            # Ingest an event strictly for Factory A
            payload = {
                "event_id": event_for_a,
                "event_type": "potential_fall",
                "event_state": "started",
                "module": "fall_detection",
                "camera_id": "camera_05",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.85,
                "attributes": {"rapid_descent": True},
            }
            res = client.post(
                "/api/v1/events/ingest",
                json=payload,
                headers={
                    "X-Camera-Key": settings.DEFAULT_CV_API_KEY,
                    "X-Factory-Id": factory_a,
                },
            )
            assert res.status_code == 201

            # Factory A's client receives the event
            msg_a = json.loads(ws_a.receive_text())
            assert msg_a["type"] == "safety_event"
            assert msg_a["data"]["event_id"] == event_for_a
            assert msg_a["factory_id"] == factory_a

            # Factory B's client should NOT have received Factory A's event.
            # Verify by sending a ping from B and confirming B only receives its own pong.
            ws_b.send_text(json.dumps({"type": "ping"}))
            msg_b = json.loads(ws_b.receive_text())
            assert msg_b["type"] == "pong"
