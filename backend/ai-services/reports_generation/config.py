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
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)


def _get_path(env_key: str, default: str) -> Path:
    val = os.getenv(env_key, default)
    p = Path(val)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_reports_storage_dir() -> Path:
    """Resolve reports storage directory dynamically from environment."""
    return _get_path("OPERIX_REPORTS_STORAGE_DIR", "storage/reports")


# Factory Scope
DEFAULT_FACTORY_ID: str = (
    os.getenv("OPERIX_FACTORY_ID")
    or os.getenv("DEFAULT_FACTORY_ID")
    or "aaaaaaaa-0001-0001-0001-000000000001"
)

# Storage
REPORTS_STORAGE_DIR: Path = get_reports_storage_dir()

# Defaults
DEFAULT_REPORT_FORMAT: str = os.getenv("OPERIX_REPORT_DEFAULT_FORMAT", "pdf").lower()
MAX_REPORT_DAYS_SPAN: int = int(os.getenv("OPERIX_MAX_REPORT_DAYS_SPAN", "365"))
