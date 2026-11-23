"""
app/schemas/__init__.py
Pydantic schemas registry.
"""
from .common import APIErrorResponse, APIResponse, APIResponseMeta, ErrorDetail
from .events import (
    CVDetection,
    CVEventIngest,
    CVFrameResultIngest,
    EventBatchIngestResponse,
    EventIngestResponse,
    EventResponse,
)
from .health import DatabaseHealth, HealthData

__all__ = [
    "APIResponse",
    "APIResponseMeta",
    "APIErrorResponse",
    "ErrorDetail",
    "DatabaseHealth",
    "HealthData",
    "CVDetection",
    "CVEventIngest",
    "CVFrameResultIngest",
    "EventResponse",
    "EventIngestResponse",
    "EventBatchIngestResponse",
]
