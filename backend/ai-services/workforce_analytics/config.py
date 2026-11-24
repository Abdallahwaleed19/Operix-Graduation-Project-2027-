"""
workforce_analytics/config.py
Loads all runtime settings from the .env file.
Never hardcode credentials here — use .env.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve .env relative to the ai-services/ root so the module works
# regardless of the working directory it is launched from.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


# ---------------------------------------------------------------------------
# Default factory scope (can be overridden per-call)
# ---------------------------------------------------------------------------
_APP_ENV: str = os.getenv("APP_ENV", "production").lower()
_TEST_MODE: bool = os.getenv("TEST_MODE", "").lower() in ("1", "true", "yes")

# Hardcoded dev-only sentinel UUID — NEVER used in production paths.
_DEV_SENTINEL_FACTORY_ID = "aaaaaaaa-0001-0001-0001-000000000001"

_env_factory_id: str = os.getenv("OPERIX_FACTORY_ID", "") or os.getenv("DEFAULT_FACTORY_ID", "")

if _env_factory_id:
    DEFAULT_FACTORY_ID: str = _env_factory_id
elif _APP_ENV in ("development", "dev", "test", "testing") or _TEST_MODE:
    # Dev/test environments may use the sentinel to allow offline testing
    DEFAULT_FACTORY_ID = _DEV_SENTINEL_FACTORY_ID
else:
    # Production: no env var set → raise immediately so the misconfiguration is caught at startup
    raise EnvironmentError(
        "OPERIX_FACTORY_ID or DEFAULT_FACTORY_ID must be set in production. "
        "Refusing to start with a hardcoded factory sentinel. "
        "Set APP_ENV=development for local development."
    )

# ---------------------------------------------------------------------------
# Analytics thresholds (configurable — no magic numbers buried in code)
# ---------------------------------------------------------------------------
LOW_PRODUCTIVITY_THRESHOLD: int  = int(os.getenv("LOW_PRODUCTIVITY_THRESHOLD", "2"))
HIGH_PRODUCTIVITY_THRESHOLD: int = int(os.getenv("HIGH_PRODUCTIVITY_THRESHOLD", "5"))
RESOLUTION_RATE_TARGET: float    = float(os.getenv("RESOLUTION_RATE_TARGET", "0.80"))
