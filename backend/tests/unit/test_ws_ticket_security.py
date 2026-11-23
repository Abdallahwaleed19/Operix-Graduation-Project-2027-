"""
tests/unit/test_ws_ticket_security.py

Unit tests for WS ticket creation, verification, and Redis key generation.
No network, no database, no Redis — pure cryptographic logic tests.
"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import (
    AuthenticationException,
    _build_token,
    _b64_decode,
    _b64_encode,
    create_access_token,
    create_ws_ticket,
    get_ws_ticket_redis_key,
    verify_ws_ticket,
)
from app.core.config import settings

import base64
import hashlib
import hmac
import json


# ── Helpers ───────────────────────────────────────────────────────────────────

_USER_ID = uuid.uuid4()
_FACTORY_ID = uuid.uuid4()


def _decode_payload(token: str) -> dict:
    """Decode the payload segment of a token without verification."""
    payload_b64 = token.split(".")[1]
    padding = len(payload_b64) % 4
    if padding:
        payload_b64 += "=" * (4 - padding)
    return json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))


def _forge_ws_ticket(
    overrides: dict | None = None,
    key: str | None = None,
    lifetime: int = 30,
) -> str:
    """Build a WS ticket with optional claim overrides, signed with given key."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(_USER_ID),
        "factory_id": str(_FACTORY_ID),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=lifetime)).timestamp()),
        "purpose": "ws_ticket",
        "iss": "operix",
        "aud": "operix_ws",
    }
    if overrides:
        payload.update(overrides)
    return _build_token(payload, key or settings.WS_TICKET_KEY)


# ── create_ws_ticket() Tests ─────────────────────────────────────────────────

class TestCreateWsTicket:
    def test_returns_tuple(self):
        token, exp_ts = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        assert isinstance(token, str)
        assert isinstance(exp_ts, int)

    def test_token_has_three_parts(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        assert len(token.split(".")) == 3

    def test_payload_contains_required_claims(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        required = {"sub", "factory_id", "jti", "iat", "exp", "purpose", "iss", "aud"}
        assert required.issubset(payload.keys())

    def test_payload_sub_matches_user_id(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["sub"] == str(_USER_ID)

    def test_payload_factory_id_matches(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["factory_id"] == str(_FACTORY_ID)

    def test_payload_jti_is_valid_uuid(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        uuid.UUID(payload["jti"])  # Raises ValueError if invalid

    def test_payload_purpose_is_ws_ticket(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["purpose"] == "ws_ticket"

    def test_payload_iss_is_operix(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["iss"] == "operix"

    def test_payload_aud_is_operix_ws(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["aud"] == "operix_ws"

    def test_lifetime_does_not_exceed_30s(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["exp"] - payload["iat"] <= 30

    def test_exp_matches_returned_timestamp(self):
        token, exp_ts = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        payload = _decode_payload(token)
        assert payload["exp"] == exp_ts

    def test_jti_is_unique_across_calls(self):
        _, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        t1_payload = _decode_payload(
            create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)[0]
        )
        t2_payload = _decode_payload(
            create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)[0]
        )
        assert t1_payload["jti"] != t2_payload["jti"]


# ── verify_ws_ticket() Tests ─────────────────────────────────────────────────

class TestVerifyWsTicket:
    def test_valid_ticket_passes(self):
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        claims = verify_ws_ticket(token)
        assert claims["sub"] == str(_USER_ID)
        assert claims["factory_id"] == str(_FACTORY_ID)

    def test_invalid_hmac_signature_rejected(self):
        """Token signed with wrong key must be rejected."""
        forged = _forge_ws_ticket(key="wrong-key-that-is-at-least-32-bytes!!")
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code in ("INVALID_SIGNATURE", "INVALID_TOKEN")

    def test_expired_ticket_rejected(self):
        """Token with exp in the past must be rejected."""
        now = datetime.now(timezone.utc)
        forged = _forge_ws_ticket(overrides={
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now - timedelta(seconds=30)).timestamp()),
        })
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "WS_TICKET_EXPIRED"

    def test_future_iat_rejected(self):
        """Token with iat more than 5s in the future must be rejected."""
        now = datetime.now(timezone.utc)
        forged = _forge_ws_ticket(overrides={
            "iat": int((now + timedelta(seconds=10)).timestamp()),
            "exp": int((now + timedelta(seconds=40)).timestamp()),
        })
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_invalid_uuid_in_sub_rejected(self):
        forged = _forge_ws_ticket(overrides={"sub": "not-a-uuid"})
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_invalid_uuid_in_factory_id_rejected(self):
        forged = _forge_ws_ticket(overrides={"factory_id": "not-a-uuid"})
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_invalid_uuid_in_jti_rejected(self):
        forged = _forge_ws_ticket(overrides={"jti": "not-a-uuid"})
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_wrong_purpose_rejected(self):
        forged = _forge_ws_ticket(overrides={"purpose": "access_token"})
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_wrong_iss_rejected(self):
        forged = _forge_ws_ticket(overrides={"iss": "not_operix"})
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_wrong_aud_rejected(self):
        forged = _forge_ws_ticket(overrides={"aud": "wrong_audience"})
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_missing_required_claim_rejected(self):
        """Token missing 'purpose' claim must be rejected."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(_USER_ID),
            "factory_id": str(_FACTORY_ID),
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=30)).timestamp()),
            # purpose is missing
            "iss": "operix",
            "aud": "operix_ws",
        }
        token = _build_token(payload, settings.WS_TICKET_KEY)
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(token)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_lifetime_over_30s_rejected(self):
        """Token with exp - iat > 30s must be rejected."""
        now = datetime.now(timezone.utc)
        forged = _forge_ws_ticket(overrides={
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=60)).timestamp()),
        })
        with pytest.raises(AuthenticationException) as exc_info:
            verify_ws_ticket(forged)
        assert exc_info.value.error_code == "INVALID_WS_TICKET"

    def test_human_jwt_rejected_by_verify_ws_ticket(self):
        """
        A human access token (signed with SECRET_KEY) MUST be rejected
        by verify_ws_ticket (which uses WS_TICKET_KEY).
        """
        human_token = create_access_token(
            {"sub": str(_USER_ID), "factory_id": str(_FACTORY_ID)}
        )
        with pytest.raises(AuthenticationException):
            verify_ws_ticket(human_token)

    def test_malformed_token_rejected(self):
        """Token with wrong number of segments must be rejected."""
        with pytest.raises(AuthenticationException):
            verify_ws_ticket("only.two")

    def test_tampered_payload_rejected(self):
        """Token with modified payload (but original signature) must be rejected."""
        token, _ = create_ws_ticket(user_id=_USER_ID, factory_id=_FACTORY_ID)
        parts = token.split(".")
        # Tamper with the payload
        payload = _decode_payload(token)
        payload["sub"] = str(uuid.uuid4())  # Different user
        tampered_payload = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        with pytest.raises(AuthenticationException):
            verify_ws_ticket(tampered_token)


# ── get_ws_ticket_redis_key() Tests ──────────────────────────────────────────

class TestGetWsTicketRedisKey:
    def test_returns_expected_format(self):
        jti = str(uuid.uuid4())
        assert get_ws_ticket_redis_key(jti) == f"operix:ws_ticket:{jti}"

    def test_different_jti_different_key(self):
        k1 = get_ws_ticket_redis_key("aaa")
        k2 = get_ws_ticket_redis_key("bbb")
        assert k1 != k2


# ── Key separation test ──────────────────────────────────────────────────────

class TestKeySeparation:
    def test_ws_ticket_key_differs_from_secret_key(self):
        """WS_TICKET_KEY and SECRET_KEY must be different signing keys."""
        assert settings.WS_TICKET_KEY != settings.SECRET_KEY
