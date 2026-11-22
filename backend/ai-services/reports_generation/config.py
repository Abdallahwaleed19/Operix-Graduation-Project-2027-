"""
reports_generation/config.py
Configuration for the automated reports generation service.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env relative to ai-services/ root
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


def _get_path(env_key: str, default: str) -> Path:
    val = os.getenv(env_key, default)
    p = Path(val)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    p.mkdir(parents=True, exist_ok=True)
    return p


# Database
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:abdallah@localhost:5432/operix_db",
)

# Factory Scope
DEFAULT_FACTORY_ID: str = os.getenv(
    "OPERIX_FACTORY_ID",
    "aaaaaaaa-0001-0001-0001-000000000001",
)

# Storage
REPORTS_STORAGE_DIR: Path = _get_path("OPERIX_REPORTS_STORAGE_DIR", "storage/reports")

# Defaults
DEFAULT_REPORT_FORMAT: str = os.getenv("OPERIX_REPORT_DEFAULT_FORMAT", "pdf").lower()
MAX_REPORT_DAYS_SPAN: int = int(os.getenv("OPERIX_MAX_REPORT_DAYS_SPAN", "365"))
