"""
workforce_analytics/api_contracts/responses.py
Pydantic v2 response schemas and standard API envelope models.

These models wrap the existing analytics schemas defined in workforce_analytics.schemas,
providing a standardized REST API response envelope for Seif's FastAPI backend and
Taqi's frontend dashboard.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from ..schemas import (
    AttendanceMetrics,
    CameraCoverage,
    IncidentAnalytics,
    ProductivityMetrics,
    WorkforceOverview,
    WorkforceSummary,
)

T = TypeVar("T")


class APIResponseMeta(BaseModel):
    """Metadata included with every API response."""
    request_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp when the response was generated.",
    )
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Factory scope of the query.",
    )
    api_version: str = Field(
        default="v1",
        description="Operix API version.",
    )


class APIResponse(BaseModel, Generic[T]):
    """Standard success envelope for all Operix API endpoints."""
    status: str = Field(default="success", description="'success' or 'error'")
    data: T = Field(description="Payload conforming to endpoint schema.")
    meta: Optional[APIResponseMeta] = Field(
        default_factory=APIResponseMeta,
        description="Standard request/response metadata.",
    )


class ErrorDetail(BaseModel):
    """Granular error breakdown for client diagnostics."""
    field: Optional[str] = Field(default=None, description="Field name triggering error.")
    issue: str = Field(description="Human-readable description of the problem.")


class APIErrorResponse(BaseModel):
    """Standardized error envelope returned on 4xx/5xx responses."""
    status: str = Field(default="error")
    error_code: str = Field(description="Machine-readable error identifier.")
    message: str = Field(description="Summary error message.")
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="List of specific validation or operational issues.",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Specific Endpoint Response Envelopes (for clear Swagger/OpenAPI docs)
# ---------------------------------------------------------------------------

class WorkforceOverviewResponse(APIResponse[WorkforceOverview]):
    """Response envelope for GET /api/v1/analytics/workforce."""
    pass


class AttendanceResponse(APIResponse[AttendanceMetrics]):
    """Response envelope for GET /api/v1/analytics/attendance."""
    pass


class IncidentAnalyticsResponse(APIResponse[IncidentAnalytics]):
    """Response envelope for GET /api/v1/analytics/incidents."""
    pass


class ProductivityResponse(APIResponse[ProductivityMetrics]):
    """Response envelope for GET /api/v1/analytics/productivity."""
    pass


class CameraCoverageResponse(APIResponse[CameraCoverage]):
    """Response envelope for GET /api/v1/analytics/camera-coverage."""
    pass


class WorkforceSummaryResponse(APIResponse[WorkforceSummary]):
    """Response envelope for GET /api/v1/analytics/summary."""
    pass
