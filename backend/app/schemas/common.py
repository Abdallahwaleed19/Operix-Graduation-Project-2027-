"""
app/schemas/common.py
Standard API response envelopes and common DTO models.
Preserves existing contracts established in workforce_analytics/api_contracts/responses.py.
"""
from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponseMeta(BaseModel):
    """Metadata included with every successful API response."""
    request_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the response was generated.",
    )
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Factory tenant scope of the query.",
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
    details: List[ErrorDetail] = Field(
        default_factory=list,
        description="List of specific validation or operational issues.",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
