"""
app/core/database.py
SQLAlchemy 2.x engine, session factory, RLS tenant isolation, and health checking.
"""
import os
from typing import Any, Dict, Generator, Optional
from uuid import UUID
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings
from .db_target import reject_operix_db
from .logging import logger

# Tests set OPERIX_REJECT_PRODUCTION_DB=1 before this module is imported.
# The production process does not set it, so the running application can use
# its own database. When the flag is set, operix_db is rejected before
# create_engine. OPERIX_ALLOW_LIVE_DB is never consulted and cannot bypass it.
# Both the process environment and the Settings object are checked: a stale
# Settings value must not be the URL that reaches create_engine.
# The string passed to create_engine is the one that was just parsed.
_database_url = settings.DATABASE_URL
if os.environ.get("OPERIX_REJECT_PRODUCTION_DB") == "1":
    reject_operix_db(os.environ.get("DATABASE_URL", ""))
    reject_operix_db(_database_url)

# ── Engine factory — supports PostgreSQL (production) and SQLite (testing) ────
_is_sqlite = _database_url.startswith("sqlite")

if _is_sqlite:
    # SQLite: single-file, no pooling, no connect_timeout (not supported)
    engine = create_engine(
        _database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DB_ECHO,
    )
else:
    # PostgreSQL: full connection pool + connect_timeout guard (10s for cloud SSL)
    engine = create_engine(
        _database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        echo=settings.DB_ECHO,
        connect_args={"connect_timeout": 10},
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a transactional SQLAlchemy session.
    Automatically commits on success or rolls back on exception.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def set_tenant_context(
    session: Session,
    factory_id: UUID,
    user_id: Optional[UUID] = None,
) -> None:
    """
    Set PostgreSQL Row-Level Security (RLS) runtime session settings.
    Companion to Operix_Core_MVP_schema.sql lines 359-368.

    On SQLite (testing), this is a safe no-op because SQLite has no
    ``set_config()`` function and no RLS support.  RLS enforcement is
    marked NOT VERIFIED in the acceptance report.

    IMPORTANT SECURITY NOTE:
    The connecting database role must not have SUPERUSER or BYPASSRLS privileges,
    otherwise PostgreSQL ignores RLS policies regardless of app.factory_id.
    """
    if _is_sqlite:
        # SQLite has no set_config() — skip silently during tests.
        # RLS isolation is NOT verified on SQLite; see acceptance report.
        return

    try:
        session.execute(
            text("""
                SELECT set_config('app.factory_id', :factory_id, true),
                       set_config('app.user_id', :user_id, true);
            """),
            {
                "factory_id": str(factory_id),
                "user_id": str(user_id) if user_id else "",
            },
        )
    except Exception as exc:
        logger.error(f"Security Alert: Failed to establish RLS tenant context for factory {factory_id}: {exc}")
        if not settings.DEBUG:
            from .errors import TenantAccessDeniedException
            raise TenantAccessDeniedException("Failed to establish secure tenant isolation context.") from exc


def check_db_connection() -> Dict[str, Any]:
    """
    Test live database connectivity and measure ping latency in milliseconds.
    """
    start_time = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "connected",
            "latency_ms": latency_ms,
            "database_url": settings.DATABASE_URL.split("@")[-1],  # Sanitized URL
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "disconnected",
            "latency_ms": latency_ms,
            "error": str(exc),
        }
