"""
app/api/v1/router.py
Unified v1 API router assembling endpoint subrouters.
"""
from fastapi import APIRouter
from .endpoints import health

api_router = APIRouter()

# Register core endpoints
api_router.include_router(health.router)
