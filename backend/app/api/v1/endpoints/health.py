"""
app/api/v1/endpoints/health.py
Health-check, readiness, and diagnostic endpoints.
"""
from typing import Any, Dict
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ....core.config import settings
from ....core.database import check_db_connection
from ....schemas.common import APIResponse, APIResponseMeta
from ....schemas.health import DatabaseHealth, HealthData

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", response_model=APIResponse[HealthData])
def health_check() -> Any:
    """
    Comprehensive system health check.
    Verifies API readiness, database ping, and AI subsystem availability.
    """
    db_status = check_db_connection()

    # Check AI subsystems availability
    # In Phase 1, only Python module importability is verified.
    # True service readiness (vector stores, model weights, API keys) is integrated in Phase 4.
    ai_status: Dict[str, str] = {}
    try:
        from workforce_analytics.services.analytics_service import WorkforceAnalyticsService
        ai_status["workforce_analytics"] = "module_loaded"
    except Exception:
        ai_status["workforce_analytics"] = "not_configured"

    try:
        from llm_rag_assistant.services.assistant_service import get_assistant_service
        ai_status["llm_rag_assistant"] = "module_loaded"
    except Exception:
        ai_status["llm_rag_assistant"] = "not_configured"

    is_healthy = db_status["status"] == "connected"

    health_payload = HealthData(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        status="healthy" if is_healthy else "degraded",
        database=DatabaseHealth(**db_status),
        components=ai_status,
    )

    meta = APIResponseMeta(
        factory_id=settings.DEFAULT_FACTORY_ID,
        api_version="v1",
    )

    response_content = {
        "status": "success" if is_healthy else "degraded",
        "data": health_payload.model_dump(mode="json"),
        "meta": meta.model_dump(mode="json"),
    }

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response_content)


@router.get("/health/live")
def liveness() -> Dict[str, str]:
    """Lightweight Kubernetes / Docker liveness probe."""
    return {"status": "alive"}
