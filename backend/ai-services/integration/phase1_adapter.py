"""
integration/phase1_adapter.py
Phase 1 Integration Adapter bridging Seif's FastAPI Main Backend Foundation
and Abdullah's AI / Analytics Service Modules.

Design Goals:
1. Zero modifications to Seif's main backend files or architecture.
2. Injects external SQLAlchemy Session / Engine into AI services safely.
3. Delegates transaction ownership to caller; never silently closes or rolls back
   an externally provided Session.
4. Preserves factory/tenant isolation and Row-Level Security (RLS) context.
5. Adapts AI service exceptions to Seif's OperixException hierarchy.
6. Does NOT instantiate a second FastAPI app or add API endpoints.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

# Ensure ai-services root is in sys.path
_AI_SERVICES_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_SERVICES_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICES_ROOT))

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# AI Services are imported lazily within each factory function
# to avoid mandatory hard dependencies (e.g. numpy, openpyxl) at module import time.

logger = logging.getLogger("OperixPhase1Adapter")


# ===========================================================================
# 1. Configuration Synchronization
# ===========================================================================

def sync_main_settings_to_ai_services(main_settings: Any) -> None:
    """
    Synchronize configuration from Seif's Main Backend Settings
    into the runtime environment consumed by AI modules.
    Safe and idempotent; does not log secret keys.
    """
    if hasattr(main_settings, "DATABASE_URL"):
        os.environ["DATABASE_URL"] = str(main_settings.DATABASE_URL)
    if hasattr(main_settings, "DEFAULT_FACTORY_ID"):
        os.environ["DEFAULT_FACTORY_ID"] = str(main_settings.DEFAULT_FACTORY_ID)
        os.environ["OPERIX_FACTORY_ID"] = str(main_settings.DEFAULT_FACTORY_ID)
    if hasattr(main_settings, "APP_ENV"):
        os.environ["APP_ENV"] = str(main_settings.APP_ENV)

    logger.info("Synchronized Main Backend settings with AI Services runtime environment.")


# ===========================================================================
# 2. Service Initialization & Session Injection Helpers
# ===========================================================================

def get_workforce_analytics_service(
    session: Optional[Session] = None,
    factory_id: Optional[UUID | str] = None,
) -> Any:
    """
    Produce a WorkforceAnalyticsService instance.
    If a database session (e.g. from get_db or get_tenant_db) is supplied,
    it is bound to the service and reused across read-only queries without
    creating additional connection pools or altering outer transactions.
    """
    from workforce_analytics.services.analytics_service import WorkforceAnalyticsService
    return WorkforceAnalyticsService(
        default_factory_id=factory_id,
        session=session,
    )


def get_llm_rag_assistant_service() -> Any:
    """
    Produce or return the singleton OperixAssistantService instance.
    Ready for RAG Q&A and agentic remediation proposals.
    """
    from llm_rag_assistant.services.assistant_service import get_assistant_service as _get_assistant_singleton
    return _get_assistant_singleton()


def get_reports_generation_service(
    session: Optional[Session] = None,
    engine: Optional[Engine] = None,
    storage_dir: Optional[Path] = None,
) -> Any:
    """
    Produce a ReportService instance.
    Injects the active database engine/session for data gathering.
    """
    from reports_generation.services.report_service import ReportService
    return ReportService(
        engine=engine,
        session=session,
        storage_dir=storage_dir,
    )


def get_incident_evidence_service(
    storage_dir: Optional[Path] = None,
) -> Any:
    """
    Produce or return the singleton EvidenceService instance.
    Exposes upload, retrieval, and cryptographic SHA-256 integrity verification.
    """
    from incident_evidence.services.evidence_service import get_evidence_service as _get_evidence_singleton
    return _get_evidence_singleton(storage_dir=storage_dir)


# ===========================================================================
# 3. Error Compatibility Adapter
# ===========================================================================

def adapt_ai_exception_to_operix_error(exc: Exception):
    """
    Optional adapter converting AI service-specific exceptions to Seif's
    OperixException hierarchy defined in backend/app/core/errors.py.
    """
    try:
        from app.core.errors import (
            OperixException,
            ResourceNotFoundException,
            TenantAccessDeniedException,
        )
    except ImportError:
        # Fallback if running outside FastAPI backend scope
        return exc

    # Evidence module exceptions
    from incident_evidence.exceptions import (
        EvidenceNotFoundError,
        EvidenceExpiredError,
        EvidencePurgedError,
        EvidenceTransactionError,
        FactoryMismatchError,
        FileSizeLimitError,
        InvalidMimeTypeError,
    )

    if isinstance(exc, EvidenceNotFoundError):
        return ResourceNotFoundException("evidence_file", str(exc))

    if isinstance(exc, FactoryMismatchError):
        return TenantAccessDeniedException(str(exc))

    if isinstance(exc, (FileSizeLimitError, InvalidMimeTypeError)):
        return OperixException(
            message=str(exc),
            status_code=400,
            error_code="INVALID_EVIDENCE_PAYLOAD",
        )

    if isinstance(exc, (EvidenceExpiredError, EvidencePurgedError)):
        return OperixException(
            message=str(exc),
            status_code=410,
            error_code="EVIDENCE_RESOURCE_GONE",
        )

    # Reports module exceptions
    from reports_generation.exceptions import (
        InvalidDateRangeError,
        InvalidReportFormatError,
        InvalidReportTypeError,
        ReportNotFoundError,
    )

    if isinstance(exc, ReportNotFoundError):
        return ResourceNotFoundException("report", str(exc))

    if isinstance(exc, (InvalidDateRangeError, InvalidReportFormatError, InvalidReportTypeError)):
        return OperixException(
            message=str(exc),
            status_code=400,
            error_code="INVALID_REPORT_REQUEST",
        )

    return OperixException(
        message=f"AI Service Error: {exc}",
        status_code=500,
        error_code="AI_SUBSYSTEM_ERROR",
    )
