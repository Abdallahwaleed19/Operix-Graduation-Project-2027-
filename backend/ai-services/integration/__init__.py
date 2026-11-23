"""
integration/__init__.py
Integration layer and adapters bridging Seif's FastAPI Main Backend
and Abdullah's AI / Analytics Service Modules.
"""
from .phase1_adapter import (
    adapt_ai_exception_to_operix_error,
    get_incident_evidence_service,
    get_llm_rag_assistant_service,
    get_reports_generation_service,
    get_workforce_analytics_service,
    sync_main_settings_to_ai_services,
)

__all__ = [
    "sync_main_settings_to_ai_services",
    "get_workforce_analytics_service",
    "get_llm_rag_assistant_service",
    "get_reports_generation_service",
    "get_incident_evidence_service",
    "adapt_ai_exception_to_operix_error",
]
