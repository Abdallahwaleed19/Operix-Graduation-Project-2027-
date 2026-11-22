"""
app/schemas/__init__.py
Pydantic schemas registry.
"""
from .common import APIErrorResponse, APIResponse, APIResponseMeta, ErrorDetail
from .health import DatabaseHealth, HealthData

__all__ = [
    "APIResponse",
    "APIResponseMeta",
    "APIErrorResponse",
    "ErrorDetail",
    "DatabaseHealth",
    "HealthData",
]
