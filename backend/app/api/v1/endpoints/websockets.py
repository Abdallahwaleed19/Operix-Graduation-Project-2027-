"""
app/api/v1/endpoints/websockets.py
Real-time WebSocket endpoints for frontend safety dashboards and mobile listeners.

Endpoints:
  /ws/events       — legacy human-JWT authentication (unchanged, backward-compatible)
  /ws/v2/events    — ticket-based authentication (Phase 2: Redis-backed, replay-safe)
"""
import asyncio
import hmac
from datetime import datetime, timezone
import json
from typing import Optional
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ....core.config import settings
from ....core.database import SessionLocal, set_tenant_context
from ....core.logging import logger
from ....core.security import (
    AuthenticationException,
    AuthorizationException,
    authenticate_websocket_connection,
    get_ws_ticket_redis_key,
    verify_ws_ticket,
)
from ....core.websocket import ws_manager
from ....models.enums import UserStatus
from ....models.tenant import FactoryMembership, User

router = APIRouter(tags=["Real-Time WebSockets"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_ws_origin_allowed(origin: Optional[str]) -> bool:
    """Validate WebSocket Origin header against configured ALLOWED_ORIGINS."""
    if not origin:
        return settings.APP_ENV.lower() != "production"
    normalized_origin = origin.strip().rstrip("/")
    allowed = [o.strip().rstrip("/") for o in settings.ALLOWED_ORIGINS if o and o.strip()]
    if "*" in allowed:
        return True
    return normalized_origin in allowed


async def _deny_ws(websocket: WebSocket, status_code: int, reason: str) -> None:
    """
    Reject a WebSocket BEFORE accept() using the HTTP denial extension
    if available, otherwise fall back to close with custom code 4xxx.

    The ``websocket.http.response`` extension is supported by Starlette ≥1.10
    and httpx2 TestClient — verified at runtime.
    """
    extensions = websocket.scope.get("extensions", {})
    if "websocket.http.response" in extensions:
        from starlette.responses import Response
        await websocket.send_denial_response(
            Response(status_code=status_code, content=reason.encode("utf-8"))
        )
    else:
        # Fallback: accept then immediately close with a custom code
        await websocket.close(code=4000 + status_code % 1000, reason=reason)


async def _revalidate_membership_loop(
    websocket: WebSocket,
    factory_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """
    Periodically recheck factory membership; close the WebSocket immediately
    if the membership is revoked or the database becomes unavailable.

    Runs as a background task registered via ``ws_manager.register_handler_task()``.
    """
    interval = settings.WS_MEMBERSHIP_CHECK_INTERVAL
    while True:
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return

        db = SessionLocal()
        try:
            set_tenant_context(db, factory_id=factory_id, user_id=user_id)
            membership = db.execute(
                select(FactoryMembership).where(
                    FactoryMembership.factory_id == factory_id,
                    FactoryMembership.user_id == user_id,
                    FactoryMembership.is_active.is_(True),
                )
            ).scalar_one_or_none()

            if membership is None:
                logger.warning(
                    f"Membership revoked: user={user_id} factory={factory_id}"
                )
                try:
                    await websocket.close(code=4006, reason="Membership revoked.")
                except Exception:
                    pass
                return

        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.error(f"Membership revalidation DB error: {exc}")
            try:
                await websocket.close(code=1013, reason="Database unavailable.")
            except Exception:
                pass
            return
        finally:
            db.close()


# ── Legacy endpoint (unchanged — backward compatible) ─────────────────────────

@router.websocket("/ws/events")
async def websocket_events_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(
        None,
        description="Cryptographic authentication token bound to authorized factory",
    ),
    factory_id: Optional[str] = Query(
        None,
        description="Tenant Factory UUID to subscribe to (must match token scope)",
    ),
) -> None:
    """
    Real-time safety events streaming channel for Toka's frontend dashboard.
    Enforces cryptographic authentication and strict multi-tenant authorization.
    Rejects missing/invalid tokens with 4401 and cross-tenant attempts with 4403.
    """
    # 0. Validate WebSocket Origin header before any auth/accept
    if not _is_ws_origin_allowed(websocket.headers.get("origin")):
        logger.warning("Legacy WebSocket rejected: unauthorized Origin.")
        await websocket.close(code=4403, reason="WebSocket origin not allowed.")
        return

    # 1. Parse requested factory_id if provided
    requested_uuid: Optional[uuid.UUID] = None
    if factory_id:
        try:
            requested_uuid = uuid.UUID(factory_id)
        except ValueError:
            await websocket.close(code=4400, reason="Invalid factory UUID format.")
            return

    # 2. Authenticate token and verify tenant scope
    try:
        authorized_factory_id, token_payload = authenticate_websocket_connection(
            token=token,
            requested_factory_id=requested_uuid,
        )
    except AuthenticationException as exc:
        logger.warning(f"WebSocket rejected: {exc.message}")
        await websocket.close(code=4401, reason=exc.message)
        return
    except AuthorizationException as exc:
        logger.warning(f"WebSocket rejected: {exc.message}")
        await websocket.close(code=4403, reason=exc.message)
        return

    # 3. Register connection under verified tenant bucket
    await ws_manager.connect(websocket, authorized_factory_id)

    # 4. Send initial handshake confirmation
    handshake_msg = {
        "type": "connection_established",
        "factory_id": str(authorized_factory_id),
        "user_id": token_payload.get("sub"),
        "status": "connected",
        "message": "Connected to Operix real-time safety stream.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await websocket.send_text(json.dumps(handshake_msg))

    try:
        while True:
            # Keep connection open and handle incoming client commands (e.g. heartbeat ping)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "").lower()
                if msg_type == "ping":
                    pong_msg = {
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await websocket.send_text(json.dumps(pong_msg))
            except json.JSONDecodeError:
                # Client sent raw text instead of JSON
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, authorized_factory_id)
    except Exception as exc:
        logger.warning(f"Unexpected WebSocket error on factory {authorized_factory_id}: {exc}")
        await ws_manager.disconnect(websocket, authorized_factory_id)


# ── Ticket-auth endpoint (Phase 2) ───────────────────────────────────────────

@router.websocket("/ws/v2/events")
async def websocket_ticket_events_endpoint(
    websocket: WebSocket,
    ticket: Optional[str] = Query(
        None,
        description="One-time WS ticket obtained from POST /api/v1/auth/ws-ticket",
    ),
) -> None:
    """
    Real-time safety events channel — ticket-based authentication (Phase 2).

    Authentication is fully completed BEFORE websocket.accept() is called.
    The ticket is consumed atomically via Redis GETDEL (replay protection).
    Active membership is revalidated every WS_MEMBERSHIP_CHECK_INTERVAL seconds.

    Rejection codes (pre-accept HTTP denial):
      400 — missing ticket
      401 — invalid/expired/replayed ticket
      403 — membership inactive
      503 — Redis or database unavailable
    """
    # ── 0. Validate Origin before ticket verification or accept ──────────────
    if not _is_ws_origin_allowed(websocket.headers.get("origin")):
        logger.warning("WS v2 rejected: unauthorized Origin.")
        await _deny_ws(websocket, 403, "WebSocket origin not allowed.")
        return

    # ── 1. Require ticket parameter ──────────────────────────────────────────
    if not ticket:
        await _deny_ws(websocket, 400, "WS ticket is required.")
        return

    # ── 2. Verify ticket signature + claims (before accept, before Redis) ────
    try:
        claims = verify_ws_ticket(ticket)
    except AuthenticationException as exc:
        await _deny_ws(websocket, 401, exc.message)
        return

    user_id = uuid.UUID(claims["sub"])
    factory_id = uuid.UUID(claims["factory_id"])
    jti = claims["jti"]

    # ── 3. Atomic GETDEL from Redis — replay protection ──────────────────────
    redis_client = getattr(websocket.app.state, "redis", None)
    if redis_client is None:
        await _deny_ws(websocket, 503, "Service temporarily unavailable.")
        return

    try:
        redis_key = get_ws_ticket_redis_key(jti)
        stored_bytes = await redis_client.getdel(redis_key)
    except Exception as exc:
        logger.error(f"Redis error during WS ticket consume: {type(exc).__name__}")
        await _deny_ws(websocket, 503, "Service temporarily unavailable.")
        return

    if stored_bytes is None:
        await _deny_ws(websocket, 401, "WS ticket not found, expired, or already used.")
        return

    # ── 4. Constant-time comparison ──────────────────────────────────────────
    if not hmac.compare_digest(stored_bytes, ticket.encode("utf-8")):
        await _deny_ws(websocket, 401, "WS ticket mismatch.")
        return

    # ── 5. Short-lived DB session — verify membership (before accept) ────────
    db = SessionLocal()
    try:
        set_tenant_context(db, factory_id=factory_id, user_id=user_id)

        user = db.get(User, user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            await _deny_ws(websocket, 403, "User account is not active.")
            return

        membership = db.execute(
            select(FactoryMembership).where(
                FactoryMembership.factory_id == factory_id,
                FactoryMembership.user_id == user_id,
                FactoryMembership.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if membership is None:
            await _deny_ws(websocket, 403, "Factory membership inactive or not found.")
            return

    except Exception as exc:
        logger.error(f"WS ticket auth DB error: {type(exc).__name__}")
        await _deny_ws(websocket, 503, "Database error during authentication.")
        return
    finally:
        db.close()

    # ── 6. All auth passed — NOW accept ──────────────────────────────────────
    await websocket.accept()
    await ws_manager.register_accepted(websocket, factory_id)

    # ── 7. Register handler task for shutdown tracking ────────────────────────
    current_task = asyncio.current_task()
    if current_task:
        ws_manager.register_handler_task(current_task)

    # ── 8. Handshake message ─────────────────────────────────────────────────
    await websocket.send_text(json.dumps({
        "type": "connection_established",
        "factory_id": str(factory_id),
        "user_id": str(user_id),
        "status": "connected",
        "message": "Connected to Operix real-time safety stream (ticket auth).",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))

    # ── 9. Start membership revalidation task ────────────────────────────────
    revalidation_task = asyncio.create_task(
        _revalidate_membership_loop(websocket, factory_id, user_id),
        name=f"revalidate-{jti[:8]}",
    )
    ws_manager.register_handler_task(revalidation_task)

    # ── 10. Main receive loop ────────────────────────────────────────────────
    try:
        while not ws_manager._shutdown_event.is_set():
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=1.0,
                )
                try:
                    msg = json.loads(data)
                    if msg.get("type", "").lower() == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }))
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning(f"WS ticket connection error factory={factory_id}: {exc}")
    finally:
        # Cancel the revalidation task before disconnecting
        revalidation_task.cancel()
        try:
            await revalidation_task
        except (asyncio.CancelledError, Exception):
            pass
        await ws_manager.disconnect(websocket, factory_id)
