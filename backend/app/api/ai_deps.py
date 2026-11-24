"""
app/api/ai_deps.py
Phase 4.1 — FastAPI dependency injection providers for AI services.

Design rules (enforced here and in tests):
  1. The canonical backend OWNS the SQLAlchemy Session lifecycle.
     AI services receive the already-open, tenant-scoped Session.
     They must NEVER commit, rollback, or close it.
  2. No second Engine or SessionLocal is instantiated here.
     All DB access flows through the existing get_tenant_db dependency.
  3. Background tasks must call get_background_session() to obtain
     their own independent Session — they MUST NOT borrow a request Session.
  4. Storage paths are resolved from the central Settings object.
     AI module consumers should read EVIDENCE_STORAGE_DIR /
     REPORTS_STORAGE_DIR from their environment (which is set at startup
     by the main process via os.environ.setdefault in app/main.py).
  5. The phase1_adapter from backend/ai-services/integration/ is used
     as-is for service instantiation.  No duplicate logic is introduced.

Coordination note for Abdullah:
  - EVIDENCE_STORAGE_DIR env var → incident_evidence/config.py EVIDENCE_STORAGE_DIR
  - REPORTS_STORAGE_DIR env var  → reports_generation/config.py OPERIX_REPORTS_STORAGE_DIR
  Both are propagated by the lifespan startup block below (see app/main.py).
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import SessionLocal, set_tenant_context
from .deps import get_current_factory_id, get_tenant_db

logger = logging.getLogger("OperixAIDeps")

# ---------------------------------------------------------------------------
# 1. AI Service Path Resolution
# ---------------------------------------------------------------------------

def get_evidence_storage_path() -> Path:
    """
    Return the canonical evidence storage directory from Settings.
    This is the single source of truth for the evidence storage location.
    The path is guaranteed to be absolute and to exist (created on startup).
    """
    return settings.evidence_storage_path


def get_reports_storage_path() -> Path:
    """
    Return the canonical reports storage directory from Settings.
    The path is guaranteed to be absolute and to exist (created on startup).
    """
    return settings.reports_storage_path


# ---------------------------------------------------------------------------
# 2. Session Injection Helpers for AI Services
# ---------------------------------------------------------------------------

def get_tenant_session_for_ai(
    db: Session = Depends(get_tenant_db),
    factory_id: UUID = Depends(get_current_factory_id),
) -> Generator[tuple[Session, UUID], None, None]:
    """
    FastAPI dependency that yields (session, factory_id).
    The session already has the tenant RLS context set.

    AI service endpoints call:
        db, factory_id = Depends(get_tenant_session_for_ai)

    Session lifecycle is owned by the canonical get_db dependency.
    AI services MUST NOT commit, rollback, or close this session.
    """
    yield db, factory_id


# ---------------------------------------------------------------------------
# 3. Background Task Session Factory
# ---------------------------------------------------------------------------

@contextmanager
def get_background_session(factory_id: UUID) -> Generator[Session, None, None]:
    """
    Context manager for background tasks that need their own independent
    database session, isolated from any active request session.

    Usage:
        with get_background_session(factory_id) as db:
            # Perform background work
            db.commit()  # background tasks own their own transaction

    Background tasks MUST use this — they must NEVER borrow a request Session.
    Request Sessions are not thread-safe and must not be shared across tasks.
    """
    db: Session = SessionLocal()
    try:
        set_tenant_context(db, factory_id=factory_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. AI Service Factory Dependencies
# ---------------------------------------------------------------------------

def _require_ai_services_on_path() -> None:
    """
    Guard: raise ImportError with a clear message if the ai-services directory
    has not been added to sys.path (i.e. the app was not started via run.py).
    """
    import sys
    import pathlib
    ai_services_root = str(
        pathlib.Path(__file__).resolve().parent.parent.parent / "ai-services"
    )
    if ai_services_root not in sys.path:
        raise ImportError(
            "backend/ai-services is not on sys.path. "
            "Start the app via backend/run.py which adds it, "
            "or set PYTHONPATH to include backend/ai-services."
        )


def get_workforce_analytics_service_dep(
    db: Session = Depends(get_tenant_db),
    factory_id: UUID = Depends(get_current_factory_id),
):
    """
    FastAPI dependency yielding a WorkforceAnalyticsService pre-bound
    to the active request session and tenant factory_id.

    The session is injected; the service must NOT create its own engine.
    """
    _require_ai_services_on_path()
    from integration.phase1_adapter import get_workforce_analytics_service
    return get_workforce_analytics_service(session=db, factory_id=factory_id)


def get_llm_assistant_service_dep():
    """
    FastAPI dependency returning the singleton OperixAssistantService.
    The LLM/RAG assistant does not use the relational database directly.
    """
    _require_ai_services_on_path()
    from integration.phase1_adapter import get_llm_rag_assistant_service
    return get_llm_rag_assistant_service()


def get_reports_service_dep(
    db: Session = Depends(get_tenant_db),
):
    """
    FastAPI dependency yielding a ReportService pre-bound to the canonical
    backend engine and the active request session.

    The canonical engine is injected so no fallback create_engine is called.
    """
    _require_ai_services_on_path()
    from app.core.database import engine as canonical_engine
    from integration.phase1_adapter import get_reports_generation_service
    storage_dir = get_reports_storage_path()
    return get_reports_generation_service(
        session=db,
        engine=canonical_engine,
        storage_dir=storage_dir,
    )


def get_evidence_service_dep():
    """
    FastAPI dependency returning the singleton EvidenceService.
    The evidence service receives its storage directory from Settings.
    The SQLAlchemy connection is passed per-call at the endpoint level.
    """
    _require_ai_services_on_path()
    from integration.phase1_adapter import get_incident_evidence_service
    storage_dir = get_evidence_storage_path()
    return get_incident_evidence_service(storage_dir=storage_dir)


# ---------------------------------------------------------------------------
# 5. Environment Synchronisation Helper (called once at lifespan startup)
# ---------------------------------------------------------------------------

def sync_ai_service_env() -> None:
    """
    Propagate canonical storage paths into the process environment so that
    Abdullah's AI module config.py files (which read from os.environ) pick
    up the centrally-configured paths without code changes.

    Call this once inside the FastAPI lifespan startup block in app/main.py:

        from app.api.ai_deps import sync_ai_service_env
        sync_ai_service_env()

    Safe to call multiple times (idempotent; uses setdefault semantics).
    Does NOT log or expose DATABASE_URL or any secret values.
    """
    evidence_path = str(settings.evidence_storage_path)
    reports_path  = str(settings.reports_storage_path)

    # incident_evidence reads EVIDENCE_STORAGE_DIR
    if not os.environ.get("EVIDENCE_STORAGE_DIR"):
        os.environ["EVIDENCE_STORAGE_DIR"] = evidence_path

    # reports_generation reads OPERIX_REPORTS_STORAGE_DIR
    if not os.environ.get("OPERIX_REPORTS_STORAGE_DIR"):
        os.environ["OPERIX_REPORTS_STORAGE_DIR"] = reports_path

    # Synchronise DATABASE_URL (already set by main.py via setdefault, but
    # repeated here for safety when ai_deps is imported standalone in tests)
    if not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = settings.DATABASE_URL

    logger.info(
        "AI service environment synchronised: "
        "EVIDENCE_STORAGE_DIR=%s  REPORTS_STORAGE_DIR=%s",
        evidence_path,
        reports_path,
    )
