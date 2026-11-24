"""
app/main.py
Main entrypoint and FastAPI application factory for Operix.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import redis.asyncio as aioredis

from .api.v1.endpoints.health import router as health_router
from .api.v1.endpoints.websockets import router as ws_router
from .api.v1.router import api_router
from .core.config import settings
from .core.database import check_db_connection
from .core.errors import register_error_handlers
from .core.logging import logger, setup_logging
from .core.websocket import ws_manager

# Synchronize os.environ so AI subservices (e.g. workforce_analytics) inherit the database URL
os.environ.setdefault("DATABASE_URL", settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and graceful shutdown lifecycle."""
    # ── Startup ───────────────────────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Phase 4.1 — Propagate canonical storage paths into AI service environment.
    # Must run before any AI service config.py is imported so they pick up the
    # centrally-configured paths rather than their own os.getenv defaults.
    try:
        from .api.ai_deps import sync_ai_service_env
        sync_ai_service_env()
    except Exception as _ai_sync_exc:  # noqa: BLE001
        logger.warning(f"AI service environment sync skipped: {_ai_sync_exc}")

    # Database connectivity check
    db_check = check_db_connection()
    if db_check["status"] == "connected":
        logger.info(f"Database connection verified: {db_check['database_url']} ({db_check['latency_ms']} ms)")
    else:
        logger.warning(f"Database unavailable at startup: {db_check.get('error')}")

    # Redis — initialise async client with connection pool
    # Never log the REDIS_URL (may contain credentials).
    redis_client: aioredis.Redis | None = None
    try:
        pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_MAX_CONNECTIONS,
            decode_responses=False,  # raw bytes for ticket storage
        )
        redis_client = aioredis.Redis(connection_pool=pool)
        # Verify connectivity — fail startup clearly if Redis is unavailable
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connection verified and pool initialised.")
    except Exception as exc:
        # Fail startup — do not start without Redis (WS ticket feature requires it)
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass
        raise RuntimeError(
            f"Redis startup failed. WS ticket feature requires a reachable Redis instance. "
            f"Check REDIS_URL configuration. Error: {exc}"
        ) from exc

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Gracefully shutting down Operix backend.")

    # 1. Close sockets and await every tracked handler and revalidation task.
    #    Redis stays open until close_all() returns. If it raises, the pool is
    #    left in place so a failed shutdown cannot close Redis underneath a
    #    handler that is still running.
    try:
        await ws_manager.close_all(timeout=10.0)
    except Exception as exc:
        logger.error(f"Error during WebSocket manager shutdown: {exc}")
        logger.error("Redis pool left open because WebSocket shutdown did not finish.")
    else:
        logger.info("WebSocket manager shutdown complete.")
        if redis_client is not None:
            try:
                await redis_client.aclose()
                logger.info("Redis connection pool closed.")
            except Exception as exc:
                logger.error(f"Error closing Redis pool: {exc}")


def create_application() -> FastAPI:
    """Factory function creating configured FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Operix Industrial AI Safety Platform — Core Backend REST API & Real-Time Engine. "
            "Integrates Computer Vision events, deterministic safety rules, multi-channel alerts, "
            "and bilingual AI assistant services."
        ),
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # Configure CORS for Toka's frontend dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register standardized error handlers
    register_error_handlers(app)

    # Root & top-level health and websocket endpoints
    app.include_router(health_router, prefix="")
    app.include_router(ws_router, prefix="")

    # API v1 routes
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/", include_in_schema=False)
    def root() -> Dict[str, str]:
        return {
            "platform": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs": "/docs",
        }

    return app


app = create_application()
