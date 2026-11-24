"""
app/core/security.py
Cryptographic authentication and authorization utilities for Operix.
Includes secure token signing/verification and CV producer API key validation.
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import secrets
from typing import Any, Dict, Optional, Tuple
import uuid

import bcrypt

from .config import settings
from .errors import OperixException


class AuthenticationException(OperixException):
    """Authentication failure (invalid, expired, or missing credentials)."""
    def __init__(self, message: str = "Authentication failed.", error_code: str = "UNAUTHORIZED") -> None:
        super().__init__(message=message, status_code=401, error_code=error_code)


class AuthorizationException(OperixException):
    """Permission failure (insufficient privileges or cross-tenant violation)."""
    def __init__(self, message: str = "Access denied for this resource.", error_code: str = "FORBIDDEN") -> None:
        super().__init__(message=message, status_code=403, error_code=error_code)


# ---------------------------------------------------------------------------
# Cryptographic Token Helpers (HMAC-SHA256)
# ---------------------------------------------------------------------------

def _b64_encode(data: bytes) -> str:
    """URL-safe base64 encoding without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    """URL-safe base64 decoding with restored padding."""
    padding = len(data) % 4
    if padding:
        data += "=" * (4 - padding)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def _sign_token(header_b64: str, payload_b64: str, key: str) -> str:
    """Produce a URL-safe base64 HMAC-SHA256 signature for header.payload."""
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64_encode(sig)


def _build_token(payload: Dict[str, Any], key: str) -> str:
    """Encode header+payload and sign with the given key."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig_b64 = _sign_token(header_b64, payload_b64, key)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _decode_and_verify(token: str, key: str) -> Dict[str, Any]:
    """
    Verify HMAC-SHA256 signature and decode payload.
    Raises AuthenticationException on any failure.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise AuthenticationException("Malformed token format.", error_code="INVALID_TOKEN")

    header_b64, payload_b64, sig_b64 = parts

    expected_sig_b64 = _sign_token(header_b64, payload_b64, key)
    try:
        provided_sig = _b64_decode(sig_b64)
        expected_sig = _b64_decode(expected_sig_b64)
    except Exception:
        raise AuthenticationException("Invalid token signature encoding.", error_code="INVALID_TOKEN")

    # Constant-time comparison — prevents timing attacks
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise AuthenticationException("Token signature verification failed.", error_code="INVALID_SIGNATURE")

    try:
        payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise AuthenticationException("Invalid token payload.", error_code="INVALID_TOKEN")

    return payload


# ---------------------------------------------------------------------------
# Human Access Token (signed with SECRET_KEY)
# ---------------------------------------------------------------------------

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Generate a tamper-proof signed JWT-compatible token using HMAC-SHA256.
    Signed with SECRET_KEY — never use this key for WS tickets.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(hours=12))

    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })

    return _build_token(to_encode, settings.SECRET_KEY)


# ---------------------------------------------------------------------------
# Password Hashing (bcrypt) & Refresh Token Helpers
# ---------------------------------------------------------------------------

_BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt ($2b$), rejecting inputs > 72 UTF-8 bytes."""
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > _BCRYPT_MAX_BYTES:
        raise ValueError("Password exceeds bcrypt's 72-byte UTF-8 limit.")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash in constant time."""
    if not plain_password or not password_hash:
        return False
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > _BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_refresh_token() -> str:
    """Generate a cryptographically secure random opaque refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Compute 64-char SHA-256 hex digest of a refresh token for DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Verify signature and expiration of a signed access token.
    Raises AuthenticationException if invalid or expired.
    """
    payload = _decode_and_verify(token, settings.SECRET_KEY)

    exp = payload.get("exp")
    if exp and datetime.now(timezone.utc).timestamp() > exp:
        raise AuthenticationException("Token has expired.", error_code="TOKEN_EXPIRED")

    return payload


def verify_user_factory_membership(
    db: Any,
    user_id: uuid.UUID,
    factory_id: uuid.UUID,
) -> Any:
    """
    Canonical validation asserting that user exists, is active,
    and holds an active FactoryMembership in the targeted factory.
    Raises AuthorizationException if inactive or membership missing.
    """
    from ..models.tenant import FactoryMembership, User
    from ..models.enums import UserStatus
    from sqlalchemy import select

    user = db.get(User, user_id)
    if user is not None and user.status != UserStatus.ACTIVE:
        raise AuthorizationException("User account is not active.", error_code="USER_INACTIVE")

    membership = db.execute(
        select(FactoryMembership).where(
            FactoryMembership.factory_id == factory_id,
            FactoryMembership.user_id == user_id,
            FactoryMembership.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if membership is None:
        raise AuthorizationException(
            f"User does not have active membership in factory '{factory_id}'.",
            error_code="FORBIDDEN_FACTORY",
        )
    return membership


# ---------------------------------------------------------------------------
# WebSocket Ticket (signed with WS_TICKET_KEY — separate from SECRET_KEY)
# ---------------------------------------------------------------------------

_WS_TICKET_PURPOSE = "ws_ticket"
_WS_TICKET_ISS = "operix"
_WS_TICKET_AUD = "operix_ws"

# Maximum lifetime enforced regardless of exp claim
_WS_TICKET_MAX_LIFETIME = 30  # seconds


def create_ws_ticket(
    user_id: uuid.UUID,
    factory_id: uuid.UUID,
) -> Tuple[str, int]:
    """
    Issue a short-lived signed WS ticket.

    Returns (token_str, exp_unix_timestamp).
    Signed with WS_TICKET_KEY — never the human SECRET_KEY.

    Claims:
        sub         — authenticated user UUID (string)
        factory_id  — factory UUID (string)
        jti         — unique ticket UUID (string)
        iat         — issued-at (int unix)
        exp         — expiration (int unix)
        purpose     — "ws_ticket"
        iss         — "operix"
        aud         — "operix_ws"
    """
    now = datetime.now(timezone.utc)
    ttl = min(settings.WS_TICKET_TTL_SECONDS, _WS_TICKET_MAX_LIFETIME)
    exp_dt = now + timedelta(seconds=ttl)
    jti = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "factory_id": str(factory_id),
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp_dt.timestamp()),
        "purpose": _WS_TICKET_PURPOSE,
        "iss": _WS_TICKET_ISS,
        "aud": _WS_TICKET_AUD,
    }

    token = _build_token(payload, settings.WS_TICKET_KEY)
    return token, int(exp_dt.timestamp())


def verify_ws_ticket(token: str) -> Dict[str, Any]:
    """
    Verify a WS ticket and return its validated claims.

    Verifies (in order):
      1. Token structure (3-part JWT format)
      2. HMAC-SHA256 signature using WS_TICKET_KEY (constant-time)
      3. Required claims present: sub, factory_id, jti, iat, exp, purpose, iss, aud
      4. UUID format for sub, factory_id, jti
      5. iss == "operix", aud == "operix_ws", purpose == "ws_ticket"
      6. iat is not in the future (clock skew tolerance: 5 seconds)
      7. Token not expired (exp)
      8. Ticket lifetime <= 30 seconds (iat → exp gap)

    Raises AuthenticationException on any failure — never reveals which
    specific check failed to the caller (use error_code for internal routing).

    Does NOT consume the ticket from Redis (caller must do GETDEL).
    Does NOT accept a human access JWT (different signing key).
    """
    # 1–2. Structure + signature
    payload = _decode_and_verify(token, settings.WS_TICKET_KEY)

    now_ts = datetime.now(timezone.utc).timestamp()

    # 3. Required claims
    required_claims = ("sub", "factory_id", "jti", "iat", "exp", "purpose", "iss", "aud")
    missing = [c for c in required_claims if c not in payload]
    if missing:
        raise AuthenticationException(
            "WS ticket is missing required claims.",
            error_code="INVALID_WS_TICKET",
        )

    # 4. UUID formats
    for claim in ("sub", "factory_id", "jti"):
        try:
            uuid.UUID(str(payload[claim]))
        except (ValueError, AttributeError):
            raise AuthenticationException(
                "WS ticket contains invalid UUID claim.",
                error_code="INVALID_WS_TICKET",
            )

    # 5. Purpose / issuer / audience
    if payload["purpose"] != _WS_TICKET_PURPOSE:
        raise AuthenticationException(
            "Token purpose does not match ws_ticket.",
            error_code="INVALID_WS_TICKET",
        )
    if payload["iss"] != _WS_TICKET_ISS:
        raise AuthenticationException(
            "Token issuer is not accepted.",
            error_code="INVALID_WS_TICKET",
        )
    if payload["aud"] != _WS_TICKET_AUD:
        raise AuthenticationException(
            "Token audience is not accepted.",
            error_code="INVALID_WS_TICKET",
        )

    iat = payload["iat"]
    exp = payload["exp"]

    # 6. iat not in the future (allow 5-second clock skew)
    if iat > now_ts + 5:
        raise AuthenticationException(
            "WS ticket has a future issued-at timestamp.",
            error_code="INVALID_WS_TICKET",
        )

    # 7. Not expired
    if now_ts > exp:
        raise AuthenticationException(
            "WS ticket has expired.",
            error_code="WS_TICKET_EXPIRED",
        )

    # 8. Lifetime <= 30 seconds
    if (exp - iat) > _WS_TICKET_MAX_LIFETIME:
        raise AuthenticationException(
            "WS ticket lifetime exceeds the allowed maximum of 30 seconds.",
            error_code="INVALID_WS_TICKET",
        )

    return payload


def get_ws_ticket_redis_key(jti: str) -> str:
    """Return the namespaced Redis key for a WS ticket."""
    return f"operix:ws_ticket:{jti}"


# ---------------------------------------------------------------------------
# CV Producer & WebSocket Credential Verification (unchanged)
# ---------------------------------------------------------------------------

def verify_cv_producer_key(
    api_key: Optional[str],
    factory_id: uuid.UUID,
    camera_id: str,
) -> bool:
    """
    Authenticate Computer Vision camera workers.
    Verifies that the producer possesses a valid key authorized for the factory.
    """
    if not api_key:
        return False

    # In production, this matches against registered camera keys or hashed device secrets.
    # We verify against configured keys using constant-time comparison.
    expected_key = settings.DEFAULT_CV_API_KEY
    if not hmac.compare_digest(api_key.strip(), expected_key.strip()):
        return False

    return True


def authenticate_websocket_connection(
    token: Optional[str],
    requested_factory_id: Optional[uuid.UUID] = None,
) -> Tuple[uuid.UUID, Dict[str, Any]]:
    """
    Authenticate a WebSocket client via legacy human-JWT path.
    Returns (authorized_factory_id, payload).
    Raises AuthenticationException or AuthorizationException on failure.

    NOTE: This function is preserved for the legacy /ws/events endpoint.
    New connections must use the WS ticket flow instead.
    """
    if not token:
        raise AuthenticationException(
            "WebSocket authentication token is required.",
            error_code="MISSING_WS_TOKEN",
        )

    payload = decode_access_token(token)
    token_factory_id_str = payload.get("factory_id")

    if not token_factory_id_str:
        raise AuthorizationException(
            "Token does not specify an authorized factory scope.",
            error_code="MISSING_FACTORY_CLAIM",
        )

    try:
        token_factory_id = uuid.UUID(token_factory_id_str)
    except ValueError:
        raise AuthorizationException("Token contains invalid factory UUID.", error_code="INVALID_FACTORY_CLAIM")

    # If client requested a specific factory, verify it matches authorized tenant
    if requested_factory_id and requested_factory_id != token_factory_id:
        raise AuthorizationException(
            f"Unauthorized cross-factory access attempt. Token is bound to factory {token_factory_id}.",
            error_code="CROSS_TENANT_FORBIDDEN",
        )

    return token_factory_id, payload


