"""
app/api/v1/endpoints/auth.py
Authentication endpoints — WS ticket issuance.
"""
import base64
import json as _json
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ....core.config import settings
from ....core.database import SessionLocal, get_db, set_tenant_context
from ....core.errors import OperixException
from ....core.logging import logger
from ....core.security import (
    AuthenticationException,
    AuthorizationException,
    create_access_token,
    create_ws_ticket,
    decode_access_token,
    generate_refresh_token,
    get_ws_ticket_redis_key,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from ....models.enums import FactoryStatus, TokenPurpose, UserStatus
from ....models.tenant import AuthToken, Factory, FactoryMembership, Role, User
from ....schemas.auth import (
    AuthUserSummary,
    LoginData,
    LoginRequest,
    LogoutData,
    LogoutRequest,
    MeData,
    RefreshRequest,
    RegisterData,
    RegisterRequest,
)
from ....schemas.common import APIResponse, APIResponseMeta
from ....services.email_service import EmailService
from ...deps import AuthenticatedUser, get_current_user_context

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


_ACCESS_TOKEN_TTL_SECONDS = 12 * 3600
_REFRESH_TOKEN_TTL_DAYS = 7
_MAX_FAILED_LOGINS = 5
_LOCKOUT_MINUTES = 15


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _resolve_active_membership(
    db: Session,
    user_id: uuid.UUID,
    requested_factory_id: Optional[uuid.UUID],
) -> tuple[FactoryMembership, Factory, Role]:
    """Resolve an active FactoryMembership + active Factory + Role for the user."""
    stmt = (
        select(FactoryMembership, Factory, Role)
        .join(Factory, Factory.id == FactoryMembership.factory_id)
        .join(Role, Role.id == FactoryMembership.role_id)
        .where(
            FactoryMembership.user_id == user_id,
            FactoryMembership.is_active.is_(True),
            Factory.status == FactoryStatus.ACTIVE,
        )
        .order_by(FactoryMembership.created_at.asc())
    )
    if requested_factory_id is not None:
        stmt = stmt.where(FactoryMembership.factory_id == requested_factory_id)
        row = db.execute(stmt).first()
        if row is None:
            raise AuthorizationException(
                "User does not have active membership in the requested factory.",
                error_code="NOT_A_MEMBER",
            )
        return row[0], row[1], row[2]

    rows = db.execute(stmt).all()
    if not rows:
        raise AuthorizationException(
            "User does not have any active factory membership.",
            error_code="NOT_A_MEMBER",
        )
    for row in rows:
        if row[1].id == settings.DEFAULT_FACTORY_ID:
            return row[0], row[1], row[2]
    return rows[0][0], rows[0][1], rows[0][2]


def _issue_session_tokens(
    db: Session,
    user: User,
    factory: Factory,
    role: Role,
    now: datetime,
) -> LoginData:
    """Create access JWT + opaque refresh token (stored hashed in AuthToken)."""
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "factory_id": str(factory.id),
            "role": role.code,
            "name": user.full_name,
            "email": user.email,
        },
        expires_delta=timedelta(seconds=_ACCESS_TOKEN_TTL_SECONDS),
    )
    refresh_token = generate_refresh_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=TokenPurpose.REFRESH,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=now + timedelta(days=_REFRESH_TOKEN_TTL_DAYS),
        )
    )
    return LoginData(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=_ACCESS_TOKEN_TTL_SECONDS,
        user=AuthUserSummary(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role.code,
            factory_id=factory.id,
            factory_name=factory.name,
        ),
    )


# ── POST /api/v1/auth/login ──────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=APIResponse[LoginData],
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT + refresh token",
    description="Validates email/password, account status, lockout, and active FactoryMembership.",
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> APIResponse[LoginData]:
    """Authenticate a human user and issue access + refresh tokens."""
    now = datetime.now(timezone.utc)
    normalized_email = body.email.strip().lower()

    user = db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    ).scalar_one_or_none()

    if user is None:
        raise AuthenticationException("Invalid email or password.", error_code="INVALID_CREDENTIALS")

    if user.status != UserStatus.ACTIVE:
        raise AuthorizationException("User account is not active.", error_code="USER_INACTIVE")

    if user.locked_until is not None and _as_utc(user.locked_until) > now:
        raise AuthorizationException(
            "Account is temporarily locked due to repeated failed logins.",
            error_code="ACCOUNT_LOCKED",
        )

    if not verify_password(body.password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= _MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=_LOCKOUT_MINUTES)
        db.commit()
        raise AuthenticationException("Invalid email or password.", error_code="INVALID_CREDENTIALS")

    _, factory, role = _resolve_active_membership(db, user.id, body.factory_id)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now

    login_data = _issue_session_tokens(db, user, factory, role, now)
    logger.info(f"User login succeeded: user={user.id} factory={factory.id} role={role.code}")
    return APIResponse(
        status="success",
        data=login_data,
        meta=APIResponseMeta(factory_id=factory.id),
    )


# ── GET /api/v1/auth/me ──────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=APIResponse[MeData],
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user context",
)
def get_me(
    user: AuthenticatedUser = Depends(get_current_user_context),
) -> APIResponse[MeData]:
    """Return the authenticated user, active factory context, and resolved role."""
    return APIResponse(
        status="success",
        data=MeData(
            user_id=user.user_id,
            factory_id=user.factory_id,
            role=user.role,
            full_name=user.full_name,
            email=user.email,
        ),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


# ── POST /api/v1/auth/refresh ────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=APIResponse[LoginData],
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
def refresh_session(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> APIResponse[LoginData]:
    """Atomically rotate a refresh token and issue a fresh access + refresh pair."""
    now = datetime.now(timezone.utc)
    token_hash = hash_refresh_token(body.refresh_token.strip())

    token_row = db.execute(
        select(AuthToken)
        .where(AuthToken.token_hash == token_hash)
        .with_for_update()
    ).scalar_one_or_none()

    if token_row is None or token_row.purpose != TokenPurpose.REFRESH:
        raise AuthenticationException("Invalid refresh token.", error_code="INVALID_REFRESH_TOKEN")

    if token_row.used_at is not None:
        # Potential replay attack: revoke all active refresh tokens for this user.
        active_tokens = db.execute(
            select(AuthToken).where(
                AuthToken.user_id == token_row.user_id,
                AuthToken.purpose == TokenPurpose.REFRESH,
                AuthToken.revoked_at.is_(None),
                AuthToken.used_at.is_(None),
            )
        ).scalars().all()
        for active in active_tokens:
            active.revoked_at = now
        db.commit()
        raise AuthenticationException("Refresh token has already been used.", error_code="TOKEN_REPLAYED")

    if token_row.revoked_at is not None:
        raise AuthenticationException("Refresh token has been revoked.", error_code="TOKEN_REVOKED")

    if _as_utc(token_row.expires_at) <= now:
        raise AuthenticationException("Refresh token has expired.", error_code="TOKEN_EXPIRED")

    user = db.get(User, token_row.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthorizationException("User account is not active.", error_code="USER_INACTIVE")

    if user.locked_until is not None and _as_utc(user.locked_until) > now:
        raise AuthorizationException("User account is locked.", error_code="ACCOUNT_LOCKED")

    _, factory, role = _resolve_active_membership(db, user.id, body.factory_id)

    token_row.used_at = now
    db.flush()

    login_data = _issue_session_tokens(db, user, factory, role, now)
    logger.info(f"Refresh token rotated: user={user.id} factory={factory.id}")
    return APIResponse(
        status="success",
        data=login_data,
        meta=APIResponseMeta(factory_id=factory.id),
    )


# ── POST /api/v1/auth/logout ─────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=APIResponse[LogoutData],
    status_code=status.HTTP_200_OK,
    summary="Revoke a refresh token on logout",
)
def logout(
    body: LogoutRequest,
    db: Session = Depends(get_db),
) -> APIResponse[LogoutData]:
    """Revoke the supplied refresh token if active."""
    now = datetime.now(timezone.utc)
    token_hash = hash_refresh_token(body.refresh_token.strip())
    token_row = db.execute(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.purpose == TokenPurpose.REFRESH,
        )
    ).scalar_one_or_none()

    revoked = False
    if token_row is not None and token_row.revoked_at is None and token_row.used_at is None:
        token_row.revoked_at = now
        revoked = True

    return APIResponse(
        status="success",
        data=LogoutData(revoked=revoked),
        meta=APIResponseMeta(),
    )


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


_SELF_REGISTER_ROLES = frozenset({"safety_supervisor", "factory_manager", "viewer", "operator"})


@router.post(
    "/register",
    response_model=APIResponse[RegisterData],
    status_code=status.HTTP_201_CREATED,
    summary="Request Account Registration (Requires Admin Approval)",
    description=(
        "Creates a pending user account (status=invited, membership inactive) and emails "
        "active factory administrators for approval."
    ),
)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> APIResponse[RegisterData]:
    normalized_email = body.email.strip().lower()
    requested_role = body.role_code.strip().lower()
    if requested_role not in _SELF_REGISTER_ROLES:
        requested_role = "safety_supervisor"

    existing = db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    ).scalar_one_or_none()
    if existing is not None:
        raise OperixException(
            message=f"An account with email '{normalized_email}' already exists.",
            status_code=409,
            error_code="USER_ALREADY_EXISTS",
        )

    factory_id = body.factory_id or settings.DEFAULT_FACTORY_ID
    factory = db.get(Factory, factory_id)
    if factory is None or factory.status != FactoryStatus.ACTIVE:
        raise OperixException(
            message="Target factory is not available.",
            status_code=404,
            error_code="FACTORY_NOT_FOUND",
        )

    role = db.execute(select(Role).where(Role.code == requested_role)).scalar_one_or_none()
    if role is None:
        role = db.execute(select(Role).where(Role.code == "safety_supervisor")).scalar_one_or_none()
    if role is None:
        raise OperixException(
            message="Requested role is not configured.",
            status_code=400,
            error_code="ROLE_NOT_FOUND",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        status=UserStatus.INVITED,
    )
    db.add(user)
    db.flush()

    membership = FactoryMembership(
        factory_id=factory.id,
        user_id=user.id,
        role_id=role.id,
        is_active=False,
    )
    db.add(membership)
    db.flush()

    admin_rows = db.execute(
        select(User.email)
        .join(FactoryMembership, FactoryMembership.user_id == User.id)
        .join(Role, Role.id == FactoryMembership.role_id)
        .where(
            FactoryMembership.factory_id == factory.id,
            FactoryMembership.is_active.is_(True),
            User.status == UserStatus.ACTIVE,
            Role.code.in_(("factory_admin", "platform_admin")),
        )
    ).scalars().all()
    admin_emails = list(dict.fromkeys(admin_rows))

    admin_notified = EmailService.send_registration_request_to_admins(
        admin_emails=admin_emails,
        applicant_name=user.full_name,
        applicant_email=user.email,
        role_name=role.name,
        factory_name=factory.name,
    )

    return APIResponse(
        status="success",
        data=RegisterData(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=role.code,
            factory_name=factory.name,
            status=user.status.value,
            admin_notified=admin_notified,
            message="Account request submitted. An administrator must approve your account before you can sign in.",
        ),
        meta=APIResponseMeta(factory_id=factory.id),
    )
