"""
tests/conftest.py
Pytest test fixtures and configuration.

SAFETY:
  This file loads .env.test at module-level, BEFORE any app.* import, so that
  Settings() is never constructed against production environment variables.

  Execution order (Python runs the file top-to-bottom):
    1. sys.path setup                — before any relative imports
    2. load_dotenv(.env.test)        — override env vars with safe test values
    3. Pre-engine safety guard       — reject operix_db after the final URL is set.
                                       OPERIX_ALLOW_LIVE_DB is ignored.
                                       Also sets OPERIX_REJECT_PRODUCTION_DB so
                                       app.core.database rejects operix_db before
                                       create_engine.
    4. get_settings.cache_clear()   — force Settings() to rebuild from new vars
    5. from app.main import ...      — engine is created only after the guard
    6. fixtures                      — the same guard runs again on Settings

  The guard parses the URL only. It does not open a connection.
"""
import os
import sys
from pathlib import Path

# ─── 1. sys.path setup ─────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(BACKEND_DIR / "ai-services") not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR / "ai-services"))

# ─── 2. Load .env.test FIRST — before the safety guard so the final DATABASE_URL
#        is what gets checked, not whatever was in the shell environment ──────────
_TEST_ENV = BACKEND_DIR / ".env.test"

if _TEST_ENV.exists():
    from dotenv import load_dotenv
    load_dotenv(_TEST_ENV, override=True)
else:
    # Minimal safe defaults if .env.test is missing
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_operix.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
    os.environ.setdefault("WS_TICKET_KEY", "test-ws-ticket-key-32bytes-min!!")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-change-in-prod-32b!")


# ─── 3. Pre-engine guard — after .env.test, before any app import ─────────────
# The flag is set first so any later import of app.core.database rejects
# operix_db before create_engine. OPERIX_ALLOW_LIVE_DB is never read.
os.environ["OPERIX_REJECT_PRODUCTION_DB"] = "1"

from app.core.db_target import enforce_configured_test_target

_configured_database_url = enforce_configured_test_target(os.environ.get("DATABASE_URL", ""))

# ─── 4. Validate the Settings object that the engine will use ────────────────
# Importing config constructs Settings. That does not open a connection.
# Reject operix_db on that object before app.main / database.py is imported.
from app.core.config import get_settings
from app.core.config import settings as _configured_settings

enforce_configured_test_target(_configured_settings.DATABASE_URL)
get_settings.cache_clear()
enforce_configured_test_target(get_settings().DATABASE_URL)

# ─── 4a. Register PostgreSQL-specific types as SQLite-compatible ─────────────
# CITEXT is a PostgreSQL extension type. SQLite's compiler can't render it.
# This MUST run before any app.* import that touches SQLAlchemy models,
# so the dialect can render CITEXT as TEXT during create_all().
if os.environ.get("DATABASE_URL", "").startswith("sqlite"):
    from sqlalchemy.dialects.postgresql import CITEXT
    from sqlalchemy.ext.compiler import compiles

    @compiles(CITEXT, "sqlite")
    def _compile_citext_sqlite(type_, compiler, **kw):
        return "TEXT"

# ─── 5. Now safe to import app modules ───────────────────────────────────────
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from app.main import create_application
from app.core.config import Settings


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Create a fresh FastAPI app instance for testing.

    Belt-and-suspenders: re-checks the parsed Settings object even though the
    module-level guard already ran. Guards at both import-time and fixture-time.
    """
    s = get_settings()
    # Settings may have normalized the URL. Reject operix_db again before use.
    # OPERIX_ALLOW_LIVE_DB is not consulted.
    enforce_configured_test_target(s.DATABASE_URL)
    return create_application()


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """Test client yielding synchronous HTTP requests."""
    test_client = TestClient(app)
    yield test_client
