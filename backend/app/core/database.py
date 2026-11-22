"""
app/core/database.py
SQLAlchemy 2.x engine, session factory, RLS tenant isolation, and health checking.
"""
from typing import Any, Dict, Generator, Optional
from uuid import UUID
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .logging import logger

# Initialize engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    echo=settings.DB_ECHO,
    connect_args={"connect_timeout": 2},
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

    IMPORTANT SECURITY NOTE:
    The connecting database role must not have SUPERUSER or BYPASSRLS privileges,
    otherwise PostgreSQL ignores RLS policies regardless of app.factory_id.
    """
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
