"""
app/api/v1/router.py
Unified v1 API router assembling endpoint subrouters.
"""
from fastapi import APIRouter
from .endpoints import (
    analytics,
    assistant,
    auth,
    events,
    evidence,
    health,
    reports,
    rules,
    websockets,
)

api_router = APIRouter()

# Register core endpoints
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(rules.router)
api_router.include_router(websockets.router)

# Register AI service endpoints (Phase 4.2)
api_router.include_router(analytics.router)
api_router.include_router(assistant.router)
api_router.include_router(reports.router)
api_router.include_router(evidence.router)
