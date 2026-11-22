"""
app/schemas/health.py
Pydantic schemas for health-check and readiness endpoints.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: str = Field(description="'connected' or 'disconnected'")
    latency_ms: float = Field(description="Database ping latency in milliseconds.")
    database_url: Optional[str] = Field(default=None, description="Sanitized connection target.")
    error: Optional[str] = Field(default=None, description="Error detail if disconnected.")


class HealthData(BaseModel):
    app_name: str
    version: str
    environment: str
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    database: DatabaseHealth
    components: Dict[str, Any] = Field(default_factory=dict)
