"""
workforce_analytics/api_contracts/__init__.py
API contract models (requests and responses) for FastAPI integration and frontend consumption.
"""
from .requests import (
    AttendanceQueryRequest,
    CameraCoverageQueryRequest,
    IncidentQueryRequest,
    ProductivityQueryRequest,
    SummaryQueryRequest,
    WorkforceQueryRequest,
)
from .responses import (
    APIErrorResponse,
    APIResponse,
    AttendanceResponse,
    CameraCoverageResponse,
    ErrorDetail,
    IncidentAnalyticsResponse,
    ProductivityResponse,
    WorkforceOverviewResponse,
    WorkforceSummaryResponse,
)

__all__ = [
    # Requests
    "WorkforceQueryRequest",
    "AttendanceQueryRequest",
    "IncidentQueryRequest",
    "ProductivityQueryRequest",
    "CameraCoverageQueryRequest",
    "SummaryQueryRequest",
    # Responses
    "APIResponse",
    "APIErrorResponse",
    "ErrorDetail",
    "WorkforceOverviewResponse",
    "AttendanceResponse",
    "IncidentAnalyticsResponse",
    "ProductivityResponse",
    "CameraCoverageResponse",
    "WorkforceSummaryResponse",
]
