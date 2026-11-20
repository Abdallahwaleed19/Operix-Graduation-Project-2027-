"""
workforce_analytics/database.py
SQLAlchemy 2.x engine + session factory.

Supports both psycopg 3 (postgresql+psycopg) and psycopg2 (postgresql+psycopg2).
The driver is selected automatically based on what is installed, or set explicitly
via DATABASE_URL in .env.

SAFETY: This module opens read-only-style sessions (no DDL, no bulk writes).
        The analytics functions only issue SELECT statements.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL

# ---------------------------------------------------------------------------
# Engine — pool_pre_ping keeps connections alive between analytics calls
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
    echo=False,          # set True temporarily for SQL debug output
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session, then close it.
    Usage:
        with get_session() as db:
            result = db.execute(text("SELECT ..."))
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with get_session() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[database] Connection failed: {exc}")
        return False
