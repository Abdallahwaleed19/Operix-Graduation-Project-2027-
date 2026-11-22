"""
app/main.py
Main entrypoint and FastAPI application factory for Operix.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .api.v1.endpoints.health import router as health_router
from .api.v1.router import api_router
from .core.config import settings
from .core.database import check_db_connection
from .core.errors import register_error_handlers
from .core.logging import logger, setup_logging

# Synchronize os.environ so AI subservices (e.g. workforce_analytics) inherit the database URL
os.environ.setdefault("DATABASE_URL", settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and graceful shutdown lifecycle."""
    # --- Startup ---
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    db_check = check_db_connection()
    if db_check["status"] == "connected":
        logger.info(f"Database connection verified: {db_check['database_url']} ({db_check['latency_ms']} ms)")
    else:
        logger.warning(f"Database unavailable at startup: {db_check.get('error')}")

    yield

    # --- Shutdown ---
    logger.info("Gracefully shutting down Operix backend.")


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

    # Root & top-level health endpoints
    app.include_router(health_router, prefix="")

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
