"""
Endpoints package.
"""
from .auth import router as auth_router
from .events import router as events_router
from .health import router as health_router
from .websockets import router as ws_router

__all__ = ["auth_router", "health_router", "events_router", "ws_router"]
