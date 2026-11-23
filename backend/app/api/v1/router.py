"""
app/api/v1/router.py
Unified v1 API router assembling endpoint subrouters.
"""
from fastapi import APIRouter
from .endpoints import auth, events, health, websockets

api_router = APIRouter()

# Register core endpoints
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(websockets.router)
