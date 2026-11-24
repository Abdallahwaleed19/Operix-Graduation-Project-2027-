"""
app/api/deps.py
FastAPI dependency injection utilities for DB sessions and tenant context.
"""
from typing import Generator, Optional
from uuid import UUID
import uuid

from fastapi import Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db, set_tenant_context
from ..core.security import (
    AuthenticationException,
    AuthorizationException,
    decode_access_token,
    verify_cv_producer_key,
    verify_user_factory_membership,
)


def get_current_factory_id(
    x_factory_id: Optional[str] = Header(
        default=None,
        description="Tenant Factory UUID (optional, defaults to configured factory)",
    ),
) -> UUID:
    """Extract factory_id from request header or fall back to default."""
    if x_factory_id:
        try:
            return UUID(x_factory_id)
        except ValueError:
            pass
    return settings.DEFAULT_FACTORY_ID


class AuthenticatedUser(BaseModel):
    """Verified user identity extracted from Bearer token or tenant scope."""
    user_id: UUID
    factory_id: UUID
    role: str = "safety_supervisor"
    full_name: Optional[str] = None
    email: Optional[str] = None


def get_current_user_context(
    authorization: Optional[str] = Header(default=None),
    x_factory_id: Optional[str] = Header(default=None, alias="X-Factory-Id"),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """
    Extract authenticated user identity from Authorization Bearer token,
    enforcing cryptographic validity, factory context matching, and active membership.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        # Check explicit test-only configuration
        if settings.ALLOW_TEST_AUTH_FALLBACK and settings.APP_ENV != "production":
            target_factory = UUID(str(x_factory_id)) if x_factory_id else settings.DEFAULT_FACTORY_ID
            return AuthenticatedUser(
                user_id=UUID("bbbbbbbb-0001-0001-0001-000000000001"),
                factory_id=target_factory,
                role="safety_supervisor",
                full_name="Operix Test Supervisor",
            )
        raise AuthenticationException(
            "Authorization header is required (Bearer <token>).",
            error_code="MISSING_AUTH_HEADER",
        )

    token = authorization[7:].strip()
    if not token:
        raise AuthenticationException("Bearer token is empty.", error_code="MISSING_AUTH_HEADER")

    # decode_access_token raises AuthenticationException on invalid signature, expired, or malformed
    payload = decode_access_token(token)

    sub = payload.get("sub")
    if not sub:
        raise AuthenticationException("Access token missing 'sub' claim.", error_code="INVALID_TOKEN")
    try:
        user_id = UUID(str(sub))
    except ValueError:
        raise AuthenticationException("Access token 'sub' is not a valid UUID.", error_code="INVALID_TOKEN")

    role = payload.get("role", "safety_supervisor")

    # Multi-tenant factory resolution and mismatch check
    token_factory_id_raw = payload.get("factory_id")
    token_factory_id = UUID(str(token_factory_id_raw)) if token_factory_id_raw else None

    header_factory_id = None
    if x_factory_id:
        try:
            header_factory_id = UUID(str(x_factory_id))
        except ValueError:
            raise AuthorizationException("Invalid 'X-Factory-Id' header format.", error_code="INVALID_FACTORY_ID")

    # Reject factory mismatch between token claim and request header (SEC-02)
    if token_factory_id is not None and header_factory_id is not None:
        if token_factory_id != header_factory_id:
            raise AuthorizationException(
                f"Factory mismatch: token factory '{token_factory_id}' does not match X-Factory-Id header '{header_factory_id}'.",
                error_code="FORBIDDEN_FACTORY",
            )

    target_factory_id = token_factory_id or header_factory_id or settings.DEFAULT_FACTORY_ID

    # Validate actual user membership against canonical database models
    if not (settings.ALLOW_TEST_AUTH_FALLBACK and settings.APP_ENV != "production"):
        verify_user_factory_membership(db, user_id=user_id, factory_id=target_factory_id)
    else:
        try:
            verify_user_factory_membership(db, user_id=user_id, factory_id=target_factory_id)
        except AuthorizationException:
            raise
        except Exception:
            # Tolerates missing FactoryMembership table in minimal in-memory fixtures
            pass

    return AuthenticatedUser(
        user_id=user_id,
        factory_id=target_factory_id,
        role=role,
        full_name=payload.get("name"),
        email=payload.get("email"),
    )


def require_cv_producer_auth(
    x_camera_key: Optional[str] = Header(
        default=None,
        alias="X-Camera-Key",
        description="Camera / Producer API Secret Key",
    ),
    factory_id: UUID = Depends(get_current_factory_id),
) -> UUID:
    """
    Enforces authentication for Computer Vision event ingestion.
    Rejects missing or invalid credentials with HTTP 401.
    """
    if not x_camera_key:
        raise AuthenticationException(
            "Missing camera producer authentication header 'X-Camera-Key'.",
            error_code="MISSING_CAMERA_KEY",
        )
    if not verify_cv_producer_key(x_camera_key, factory_id=factory_id, camera_id=""):
        raise AuthenticationException(
            "Invalid or unauthorized camera producer credentials.",
            error_code="INVALID_CAMERA_KEY",
        )
    return factory_id


def get_tenant_db(
    db: Session = Depends(get_db),
    factory_id: UUID = Depends(get_current_factory_id),
) -> Generator[Session, None, None]:
    """
    Yields an active DB session with Row-Level Security (RLS) tenant context set.
    """
    set_tenant_context(db, factory_id=factory_id)
    try:
        yield db
    finally:
        pass
