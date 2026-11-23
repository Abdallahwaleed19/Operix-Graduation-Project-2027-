"""
app/api/v1/endpoints/auth.py
Authentication endpoints — WS ticket issuance.
"""
import base64
import json as _json
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from ....core.config import settings
from ....core.database import SessionLocal, set_tenant_context
from ....core.errors import OperixException
from ....core.logging import logger
from ....core.security import (
    AuthenticationException,
    AuthorizationException,
    create_ws_ticket,
    decode_access_token,
    get_ws_ticket_redis_key,
)
from ....models.tenant import FactoryMembership, User
from ....models.enums import UserStatus
from ....schemas.common import APIResponse, APIResponseMeta

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request / Response Schemas ────────────────────────────────────────────────

class WsTicketRequest(BaseModel):
    factory_id: uuid.UUID = Field(..., description="Factory UUID the client wants to connect to.")


class WsTicketData(BaseModel):
    ticket: str = Field(..., description="Short-lived signed WS ticket. Use within exp seconds.")
    expires_at: int = Field(..., description="Unix timestamp after which the ticket is invalid.")
    expires_in_seconds: int = Field(..., description="Seconds until ticket expiry.")
    factory_id: str = Field(..., description="Factory the ticket is bound to.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_bearer(authorization: str | None) -> str:
    """Extract Bearer token from Authorization header; raises 401 if missing/malformed."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationException(
            "Authorization header is required (Bearer <token>).",
            error_code="MISSING_AUTH_HEADER",
        )
    token = authorization[7:].strip()
    if not token:
        raise AuthenticationException("Bearer token is empty.", error_code="MISSING_AUTH_HEADER")
    return token


def _extract_jti_from_ticket(ticket_token: str) -> str:
    """Decode the payload segment of a just-created ticket to retrieve jti."""
    raw = ticket_token.split(".")[1]
    pad = len(raw) % 4
    if pad:
        raw += "=" * (4 - pad)
    return _json.loads(base64.urlsafe_b64decode(raw.encode()).decode())["jti"]


# ── POST /api/v1/auth/ws-ticket ───────────────────────────────────────────────

@router.post(
    "/ws-ticket",
    response_model=APIResponse[WsTicketData],
    status_code=status.HTTP_200_OK,
    summary="Issue a one-time WebSocket authentication ticket",
    description=(
        "Exchanges a valid human JWT for a short-lived (≤30 s) signed WS ticket. "
        "The ticket is stored atomically in Redis and consumed on first use. "
        "Requires active factory membership. Fails closed if Redis is unavailable."
    ),
)
async def issue_ws_ticket(
    body: WsTicketRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> APIResponse[WsTicketData]:
    """
    Issue a one-time WS authentication ticket.

    Flow:
      1. Verify human JWT (Authorization: Bearer <token>).
      2. Extract user_id (sub) from verified payload.
      3. Open short-lived DB session.
      4. Set both tenant context values (factory_id + user_id).
      5. Verify user is active.
      6. Verify active FactoryMembership.
      7. Close DB session.
      8. Generate unique jti + signed ticket (WS_TICKET_KEY, never SECRET_KEY).
      9. Store ticket bytes in Redis under operix:ws_ticket:{jti} with TTL.
      10. Return ticket to client (never log the ticket value).
    """
    # 1. Verify human JWT
    raw_token = _require_bearer(authorization)
    try:
        human_payload = decode_access_token(raw_token)
    except AuthenticationException:
        raise
    except Exception as exc:
        raise AuthenticationException("Failed to verify access token.", error_code="INVALID_TOKEN") from exc

    # 2. Extract user_id from "sub" claim
    sub = human_payload.get("sub")
    if not sub:
        raise AuthenticationException("Access token missing 'sub' claim.", error_code="INVALID_TOKEN")
    try:
        user_id = uuid.UUID(str(sub))
    except ValueError:
        raise AuthenticationException("Access token 'sub' is not a valid UUID.", error_code="INVALID_TOKEN")

    factory_id = body.factory_id

    # 3-7. Short-lived DB session — verify user + membership
    db = SessionLocal()
    try:
        # 4. Set both tenant context values before any query
        set_tenant_context(db, factory_id=factory_id, user_id=user_id)

        # 5. Verify user exists and is active
        user = db.get(User, user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise AuthorizationException("User account is not active.", error_code="USER_INACTIVE")

        # 6. Verify active factory membership
        membership = db.execute(
            select(FactoryMembership).where(
                FactoryMembership.factory_id == factory_id,
                FactoryMembership.user_id == user_id,
                FactoryMembership.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if membership is None:
            raise AuthorizationException(
                "User does not have active membership in the requested factory.",
                error_code="NOT_A_MEMBER",
            )

    except (AuthenticationException, AuthorizationException):
        raise
    except Exception as exc:
        logger.error(f"WS ticket DB check failed: {type(exc).__name__}")
        raise OperixException(
            message="Database error during membership verification.",
            status_code=503,
            error_code="DB_UNAVAILABLE",
        ) from exc
    finally:
        db.close()  # 7. Close session before any Redis operation

    # 8. Generate ticket (signed with WS_TICKET_KEY, never SECRET_KEY)
    ticket_token, exp_ts = create_ws_ticket(user_id=user_id, factory_id=factory_id)

    # 9. Store ticket in Redis — fail closed if Redis is unavailable
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise OperixException(
            message="Redis is unavailable. Cannot issue WS ticket.",
            status_code=503,
            error_code="REDIS_UNAVAILABLE",
        )

    try:
        jti = _extract_jti_from_ticket(ticket_token)
        redis_key = get_ws_ticket_redis_key(jti)
        await redis.set(
            redis_key,
            ticket_token.encode("utf-8"),
            ex=settings.WS_TICKET_TTL_SECONDS,
        )
    except Exception as exc:
        logger.error("Redis error during WS ticket storage.")
        raise OperixException(
            message="Failed to store WS ticket. Redis may be unavailable.",
            status_code=503,
            error_code="REDIS_UNAVAILABLE",
        ) from exc

    now_ts = int(datetime.now(timezone.utc).timestamp())
    expires_in = max(0, exp_ts - now_ts)

    # Never log the ticket token value
    logger.info(f"WS ticket issued for user={user_id} factory={factory_id} expires_in={expires_in}s")

    return APIResponse(
        status="success",
        data=WsTicketData(
            ticket=ticket_token,
            expires_at=exp_ts,
            expires_in_seconds=expires_in,
            factory_id=str(factory_id),
        ),
        meta=APIResponseMeta(factory_id=factory_id),
    )
