"""
tests/test_cors_and_ws_origin.py
Phase 5 Milestone 1 (S-5) — CORS, .env.example, and WebSocket Origin validation tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import uuid

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings, settings
from app.core.database import SessionLocal
from app.core.security import create_ws_ticket, get_ws_ticket_redis_key
from app.main import create_application
from app.models.base import Base
from app.models.enums import FactoryStatus, UserStatus
from app.models.tenant import Factory, FactoryMembership, Role, User


class _FakeAsyncRedis:
    """Minimal async Redis double for offline WS v2 origin tests."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def set(self, key: str, value: bytes, ex: int | None = None) -> None:
        self._store[key] = value

    async def getdel(self, key: str) -> bytes | None:
        return self._store.pop(key, None)


def _extract_jti(ticket: str) -> str:
    import base64
    import json

    raw = ticket.split(".")[1]
    pad = len(raw) % 4
    if pad:
        raw += "=" * (4 - pad)
    return json.loads(base64.urlsafe_b64decode(raw.encode()).decode())["jti"]


class TestCorsConfiguration:
    def test_allowed_localhost_origins(self):
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            app = create_application()
            client = TestClient(app)

            for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
                resp = client.get("/api/v1/health", headers={"Origin": origin})
                assert resp.status_code == 200
                assert resp.headers.get("access-control-allow-origin") == origin
                assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_rejected_unauthorized_origin(self):
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            app = create_application()
            client = TestClient(app)

            resp = client.get("/api/v1/health", headers={"Origin": "https://evil.example.com"})
            assert "access-control-allow-origin" not in resp.headers

    def test_options_preflight_allows_auth_and_factory_headers(self):
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            app = create_application()
            client = TestClient(app)

            resp = client.options(
                "/api/v1/analytics/summary",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization, X-Factory-Id, Content-Type",
                },
            )
            assert resp.status_code == 200
            assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
            assert resp.headers.get("access-control-allow-credentials") == "true"
            allowed_headers = resp.headers.get("access-control-allow-headers", "").lower()
            assert "authorization" in allowed_headers
            assert "x-factory-id" in allowed_headers
            assert "content-type" in allowed_headers

    def test_options_preflight_rejects_unauthorized_origin(self):
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            app = create_application()
            client = TestClient(app)

            resp = client.options(
                "/api/v1/auth/ws-ticket",
                headers={
                    "Origin": "https://evil.example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Authorization, Content-Type",
                },
            )
            assert resp.status_code == 400
            assert "access-control-allow-origin" not in resp.headers

    def test_env_example_loads_valid_settings(self):
        env_example_path = Path(__file__).resolve().parent.parent / ".env.example"
        assert env_example_path.exists()
        raw_values = dotenv_values(env_example_path)
        for key in (
            "WS_TICKET_KEY",
            "REDIS_URL",
            "ALLOWED_ORIGINS",
            "EVIDENCE_STORAGE_DIR",
            "REPORTS_STORAGE_DIR",
            "ALLOW_TEST_AUTH_FALLBACK",
        ):
            assert key in raw_values, f"Missing {key} in .env.example"

        loaded = Settings(**raw_values)
        assert loaded.ALLOWED_ORIGINS == [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]


class TestWebSocketOriginValidation:
    def test_ws_v2_rejects_unauthorized_origin(self):
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            app = create_application()
            client = TestClient(app)

            with pytest.raises(Exception):
                with client.websocket_connect(
                    "/ws/v2/events?ticket=dummy",
                    headers={"Origin": "https://evil.example.com"},
                ):
                    pass

    def test_ws_legacy_rejects_unauthorized_origin(self):
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            app = create_application()
            client = TestClient(app)

            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(
                    "/ws/events?token=dummy",
                    headers={"Origin": "https://evil.example.com"},
                ):
                    pass
            assert exc_info.value.code == 4403

    def test_ws_v2_accepts_allowed_localhost_origin_with_valid_ticket(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            bind=engine,
            tables=[Factory.__table__, Role.__table__, User.__table__, FactoryMembership.__table__],
        )
        TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        factory_id = uuid.uuid4()
        user_id = uuid.uuid4()
        role_id = uuid.uuid4()
        db = TestingSession()
        db.add(Factory(id=factory_id, name="Plant 1", slug="plant-1", status=FactoryStatus.ACTIVE))
        db.add(Role(id=role_id, code="safety_supervisor", name="Safety Supervisor"))
        db.add(
            User(
                id=user_id,
                email="sup@plant1.example",
                password_hash="$2b$12$fakehash",
                full_name="Supervisor",
                status=UserStatus.ACTIVE,
                activated_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            FactoryMembership(
                factory_id=factory_id,
                user_id=user_id,
                role_id=role_id,
                is_active=True,
            )
        )
        db.commit()
        db.close()

        app = create_application()
        fake_redis = _FakeAsyncRedis()
        app.state.redis = fake_redis

        ticket, _ = create_ws_ticket(user_id=user_id, factory_id=factory_id)
        jti = _extract_jti(ticket)
        fake_redis._store[get_ws_ticket_redis_key(jti)] = ticket.encode("utf-8")

        client = TestClient(app)
        with patch.object(settings, "ALLOWED_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"]):
            with patch("app.api.v1.endpoints.websockets.SessionLocal", TestingSession):
                with patch("app.api.v1.endpoints.websockets.set_tenant_context"):
                    with client.websocket_connect(
                        f"/ws/v2/events?ticket={ticket}",
                        headers={"Origin": "http://localhost:5173"},
                    ) as ws:
                        msg = ws.receive_json()
                        assert msg["type"] == "connection_established"
                        assert msg["factory_id"] == str(factory_id)
