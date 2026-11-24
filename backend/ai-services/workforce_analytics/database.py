"""
workforce_analytics/database.py
Session compatibility shim for Workforce Analytics.

IMPORTANT:
  - Local SQLAlchemy Engine / SessionLocal creation has been removed.
  - All database connections and transactions are owned by the canonical Backend.
  - Callers MUST inject an open SQLAlchemy Session into analytics functions
    or WorkforceAnalyticsService.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Local session creation is disabled.
    Always inject the canonical Backend SQLAlchemy Session instead.
    """
    raise RuntimeError(
        "Local database engine/session creation is disabled in workforce_analytics. "
        "Inject a canonical Backend SQLAlchemy Session."
    )
    yield  # pragma: no cover


def test_connection(session: Optional[Session] = None) -> bool:
    """
    Verify database connectivity using an injected Session.
    Never creates an independent Engine or Session.
    """
    if session is None:
        return False
    try:
        session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
