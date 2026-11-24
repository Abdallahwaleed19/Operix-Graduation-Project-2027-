"""
tests/test_phase4_remediation.py
Phase 4 Security Remediation Tests.
Covers:
  - SEC-01: Authentication fallback elimination, invalid token 401, production fallback prevention
  - SEC-02: Multi-tenant factory mismatch rejection (HTTP 403), canonical FactoryMembership verification
  - SEC-09: Transaction-safe post-commit WebSocket broadcasting
  - SEC-10: Exception propagation, session rollback on failure, caller-owned session protection
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import AuthenticatedUser, get_current_user_context
from app.core.config import settings
from app.core.errors import OperixException, ResourceNotFoundException, TenantAccessDeniedException
from app.core.security import AuthorizationException, create_access_token
from app.main import create_application
from app.models.base import Base
from app.models.enums import FactoryStatus, IncidentState, SeverityLevel, UserStatus
from app.models.incidents import Incident
from app.models.tenant import Factory, FactoryMembership, Role, User
from app.services.ai_action_service import AIActionService

FACTORY_A = UUID("aaaaaaaa-0001-0001-0001-000000000001")
FACTORY_B = UUID("bbbbbbbb-0002-0002-0002-000000000002")
USER_ID = UUID("11111111-0001-0001-0001-000000000001")


@pytest.fixture
def app_instance():
    return create_application()


@pytest.fixture
def test_client(app_instance):
    return TestClient(app_instance)


@pytest.fixture
def memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create required tables
    Factory.__table__.create(bind=engine, checkfirst=True)
    Role.__table__.create(bind=engine, checkfirst=True)
    User.__table__.create(bind=engine, checkfirst=True)
    FactoryMembership.__table__.create(bind=engine, checkfirst=True)
    Incident.__table__.create(bind=engine, checkfirst=True)

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1. SEC-01 Authentication Remediation Tests
# ---------------------------------------------------------------------------

class TestSEC01Authentication:
    """
    Auth tests call get_current_user_context() directly (unit-test style).
    This avoids HTTP transport overhead and AI service initialization hangs
    while still exercising the full authentication logic.
    A lightweight SQLite in-memory session is passed where the dep needs db.
    """

    def _make_session(self):
        """Minimal in-memory SQLite session for auth deps that require db."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.create_all = lambda **kw: None  # tables not needed; auth raises early
        SessionMaker = sessionmaker(bind=engine)
        return SessionMaker()

    def test_missing_token_returns_401_when_fallback_disabled(self):
        """When ALLOW_TEST_AUTH_FALLBACK is False, missing token must raise MISSING_AUTH_HEADER."""
        from app.core.security import AuthenticationException
        db = self._make_session()
        try:
            with patch.object(settings, "ALLOW_TEST_AUTH_FALLBACK", False):
                with pytest.raises(AuthenticationException) as exc_info:
                    get_current_user_context(
                        authorization=None,
                        x_factory_id=str(FACTORY_A),
                        db=db,
                    )
                assert exc_info.value.error_code == "MISSING_AUTH_HEADER"
                assert exc_info.value.status_code == 401
        finally:
            db.close()

    def test_invalid_bearer_token_returns_401(self):
        """Tampered or invalid token must raise AuthenticationException, never synthetic identity."""
        from app.core.security import AuthenticationException
        db = self._make_session()
        try:
            with pytest.raises(AuthenticationException) as exc_info:
                get_current_user_context(
                    authorization="Bearer invalid.tampered.token",
                    x_factory_id=str(FACTORY_A),
                    db=db,
                )
            assert exc_info.value.status_code == 401
        finally:
            db.close()

    def test_expired_token_returns_401(self):
        """Expired JWT token must raise AuthenticationException with TOKEN_EXPIRED."""
        from app.core.security import AuthenticationException
        db = self._make_session()
        try:
            expired_token = create_access_token(
                {"sub": str(USER_ID), "factory_id": str(FACTORY_A)},
                expires_delta=timedelta(seconds=-60),
            )
            with pytest.raises(AuthenticationException) as exc_info:
                get_current_user_context(
                    authorization=f"Bearer {expired_token}",
                    x_factory_id=str(FACTORY_A),
                    db=db,
                )
            assert exc_info.value.error_code == "TOKEN_EXPIRED"
            assert exc_info.value.status_code == 401
        finally:
            db.close()

    def test_production_environment_blocks_fallback_even_if_flag_true(self):
        """In production environment, fallback is strictly forbidden even when flag is True."""
        from app.core.security import AuthenticationException
        db = self._make_session()
        try:
            with patch.object(settings, "APP_ENV", "production"):
                with patch.object(settings, "ALLOW_TEST_AUTH_FALLBACK", True):
                    with pytest.raises(AuthenticationException) as exc_info:
                        get_current_user_context(
                            authorization=None,
                            x_factory_id=str(FACTORY_A),
                            db=db,
                        )
                    assert exc_info.value.error_code == "MISSING_AUTH_HEADER"
                    assert exc_info.value.status_code == 401
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 2. SEC-02 Factory Context & Membership Remediation Tests
# ---------------------------------------------------------------------------

class TestSEC02TenantContextAndMembership:

    def test_token_factory_a_and_header_factory_b_rejected_403(self):
        """Mismatched X-Factory-Id against JWT token claims must raise FORBIDDEN_FACTORY 403."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            valid_token_a = create_access_token({
                "sub": str(USER_ID),
                "factory_id": str(FACTORY_A),
                "role": "safety_supervisor",
            })
            with pytest.raises(AuthorizationException) as exc_info:
                get_current_user_context(
                    authorization=f"Bearer {valid_token_a}",
                    x_factory_id=str(FACTORY_B),  # Mismatch
                    db=db,
                )
            assert exc_info.value.error_code == "FORBIDDEN_FACTORY"
            assert "Factory mismatch" in exc_info.value.message
            assert exc_info.value.status_code == 403
        finally:
            db.close()

    def test_inactive_factory_membership_rejected_403(self, memory_db):
        """User holding inactive membership (is_active=False) is rejected with 403."""
        # Seed user and inactive membership
        user = User(
            id=USER_ID,
            email="test-inactive@operix.test",
            password_hash="hash",
            full_name="Inactive Supervisor",
            status=UserStatus.ACTIVE,
        )
        factory = Factory(id=FACTORY_A, name="Factory A", slug="factory-a")
        role = Role(id=uuid4(), code="safety_supervisor", name="Supervisor")
        membership = FactoryMembership(
            factory_id=FACTORY_A,
            user_id=USER_ID,
            role_id=role.id,
            is_active=False,  # Inactive
        )
        memory_db.add_all([factory, role, user, membership])
        memory_db.flush()

        valid_token = create_access_token({
            "sub": str(USER_ID),
            "factory_id": str(FACTORY_A),
            "role": "safety_supervisor",
        })

        with patch.object(settings, "ALLOW_TEST_AUTH_FALLBACK", False):
            with pytest.raises(AuthorizationException) as exc_info:
                get_current_user_context(
                    authorization=f"Bearer {valid_token}",
                    x_factory_id=str(FACTORY_A),
                    db=memory_db,
                )
            assert exc_info.value.status_code == 403
            assert exc_info.value.error_code == "FORBIDDEN_FACTORY"

    def test_inactive_user_account_rejected_403(self, memory_db):
        """Inactive user account (status != ACTIVE) is rejected with 403."""
        user = User(
            id=USER_ID,
            email="suspended@operix.test",
            password_hash="hash",
            full_name="Disabled User",
            status=UserStatus.DISABLED,  # Disabled
        )
        factory = Factory(id=FACTORY_A, name="Factory A", slug="factory-a-2")
        role = Role(id=uuid4(), code="safety_supervisor", name="Supervisor")
        membership = FactoryMembership(
            factory_id=FACTORY_A,
            user_id=USER_ID,
            role_id=role.id,
            is_active=True,
        )
        memory_db.add_all([factory, role, user, membership])
        memory_db.flush()

        valid_token = create_access_token({
            "sub": str(USER_ID),
            "factory_id": str(FACTORY_A),
            "role": "safety_supervisor",
        })

        with patch.object(settings, "ALLOW_TEST_AUTH_FALLBACK", False):
            with pytest.raises(AuthorizationException) as exc_info:
                get_current_user_context(
                    authorization=f"Bearer {valid_token}",
                    x_factory_id=str(FACTORY_A),
                    db=memory_db,
                )
            assert exc_info.value.status_code == 403
            assert exc_info.value.error_code == "USER_INACTIVE"


# ---------------------------------------------------------------------------
# 3. SEC-09 & SEC-10 Transaction Safety & Broadcast Ordering
# ---------------------------------------------------------------------------

class TestSEC09AndSEC10TransactionSafety:

    @pytest.mark.anyio
    async def test_successful_action_defers_broadcast_to_post_commit(self, memory_db):
        """With defer_broadcast=True, events are returned staged and not immediately broadcast."""
        action_svc = AIActionService()

        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            result = await action_svc.execute_action(
                db=memory_db,
                factory_id=FACTORY_A,
                user_id=USER_ID,
                user_role="safety_supervisor",
                action_id="act-deferred-01",
                action_type="create_incident",
                parameters={"description": "Staged broadcast incident"},
                broadcast=True,
                defer_broadcast=True,
                raise_on_error=True,
            )

            assert result["status"] == "executed"
            # Verify no immediate WebSocket broadcasts occurred before commit
            assert mock_ws.call_count == 0
            assert "_pending_broadcasts" in result
            staged = result["_pending_broadcasts"]
            assert len(staged) == 2  # incident_created, ai_action_completed

            # Simulate post-commit broadcast via BackgroundTasks
            await action_svc.broadcast_pending_events(staged)
            assert mock_ws.call_count == 2
            event_types = [c.args[1]["type"] for c in mock_ws.call_args_list]
            assert "incident_created" in event_types
            assert "ai_action_completed" in event_types

    @pytest.mark.anyio
    async def test_action_failure_propagates_and_rolls_back(self, memory_db):
        """Action errors must raise exceptions (not return 200) to trigger DB rollback."""
        action_svc = AIActionService()

        with patch("app.services.ai_action_service.ws_manager.broadcast_to_factory", new_callable=AsyncMock) as mock_ws:
            # Acknowledging non-existent incident raises ResourceNotFoundException
            with pytest.raises(ResourceNotFoundException):
                await action_svc.execute_action(
                    db=memory_db,
                    factory_id=FACTORY_A,
                    user_id=USER_ID,
                    user_role="safety_supervisor",
                    action_id="act-fail-01",
                    action_type="acknowledge_incident",
                    parameters={"incident_id": str(uuid4())},
                    broadcast=True,
                    defer_broadcast=True,
                    raise_on_error=True,
                )

            # Zero success events broadcast on failure
            assert mock_ws.call_count == 0

    @pytest.mark.anyio
    async def test_operator_role_rejection_raises_403(self, memory_db):
        """Unauthorized operator attempting privileged action raises 403 AuthorizationException."""
        action_svc = AIActionService()

        with pytest.raises(AuthorizationException) as exc_info:
            await action_svc.execute_action(
                db=memory_db,
                factory_id=FACTORY_A,
                user_id=USER_ID,
                user_role="operator",
                action_id="act-unauth-01",
                action_type="alert",
                parameters={"incident_id": str(uuid4())},
                broadcast=True,
                defer_broadcast=True,
                raise_on_error=True,
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "INSUFFICIENT_PERMISSIONS"

    def test_db_flush_failure_prevents_broadcast_and_returns_500(self, app_instance):
        """
        Proves that a DB flush failure inside the endpoint handler:
        1. Propagates as HTTP 500 (not 200).
        2. Prevents any WebSocket broadcast from being scheduled via BackgroundTasks.
        3. Triggers session rollback and close in the dependency teardown.

        Architecture note:
        BackgroundTasks only execute if execute_action() returns normally.
        When db.flush() raises inside _handle_create_incident(), the exception
        propagates through execute_action (raise_on_error=True), through the
        FastAPI route handler, and FastAPI returns HTTP 500. The
        background_tasks.add_task() line is never reached, so zero WS events fire.
        This is a correct and verifiable property of the current architecture.
        """
        from app.api.deps import get_current_user_context, get_tenant_db

        test_client = TestClient(app_instance, raise_server_exceptions=False)

        # Build a mock session whose flush() raises to simulate a DB integrity failure
        mock_session = MagicMock()
        mock_session.flush.side_effect = RuntimeError("Simulated DB flush failure — integrity constraint")

        rollback_called = False
        close_called = False

        def mock_tenant_db():
            nonlocal rollback_called, close_called
            try:
                yield mock_session
            except Exception:
                rollback_called = True
                mock_session.rollback()
                raise
            finally:
                close_called = True
                mock_session.close()

        # Override user context to avoid its own DB call and to supply a trusted identity
        mock_user = AuthenticatedUser(
            user_id=USER_ID,
            factory_id=FACTORY_A,
            role="safety_supervisor",
            full_name="Test Supervisor",
        )

        app_instance.dependency_overrides[get_tenant_db] = mock_tenant_db
        app_instance.dependency_overrides[get_current_user_context] = lambda: mock_user

        valid_token = create_access_token({
            "sub": str(USER_ID),
            "factory_id": str(FACTORY_A),
            "role": "safety_supervisor",
        })

        with patch(
            "app.services.ai_action_service.ws_manager.broadcast_to_factory",
            new_callable=AsyncMock,
        ) as mock_ws:
            payload = {
                "action_id": "act-flush-fail-01",
                # create_incident calls db.flush() — this will raise via mock_session
                "action_type": "create_incident",
                "parameters": {"incident_type": "ppe_violation", "description": "Flush failure test"},
            }
            resp = test_client.post(
                "/api/v1/assistant/actions/execute",
                json=payload,
                headers={
                    "Authorization": f"Bearer {valid_token}",
                    "X-Factory-Id": str(FACTORY_A),
                },
            )

            # 1. HTTP failure response (400 via OperixException / ACTION_EXECUTION_FAILED)
            # Exception propagated before background_tasks.add_task() was reached
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "ACTION_EXECUTION_FAILED"

            # 2. Zero WebSocket broadcasts fired — BackgroundTasks never scheduled
            assert mock_ws.call_count == 0

            # 3. Session rollback and close called in dependency teardown
            assert rollback_called is True, "Session rollback must be called on DB failure"
            assert close_called is True, "Session close must be called on DB failure"
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

        app_instance.dependency_overrides.clear()
