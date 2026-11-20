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


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}. "
            f"Copy .env.example → .env and fill in the value."
        )
    return value


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = _require("DATABASE_URL")

# ---------------------------------------------------------------------------
# Default factory scope (can be overridden per-call)
# ---------------------------------------------------------------------------
DEFAULT_FACTORY_ID: str = _require("OPERIX_FACTORY_ID")

# ---------------------------------------------------------------------------
# Analytics thresholds (configurable — no magic numbers buried in code)
# ---------------------------------------------------------------------------
LOW_PRODUCTIVITY_THRESHOLD: int  = int(os.getenv("LOW_PRODUCTIVITY_THRESHOLD", "2"))
HIGH_PRODUCTIVITY_THRESHOLD: int = int(os.getenv("HIGH_PRODUCTIVITY_THRESHOLD", "5"))
RESOLUTION_RATE_TARGET: float    = float(os.getenv("RESOLUTION_RATE_TARGET", "0.80"))
