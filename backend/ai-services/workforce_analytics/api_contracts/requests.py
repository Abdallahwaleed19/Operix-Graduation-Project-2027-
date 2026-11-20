"""
workforce_analytics/api_contracts/requests.py
Pydantic v2 request query parameter models for proposed FastAPI endpoints.

Endpoints:
  - GET /api/v1/analytics/workforce
  - GET /api/v1/analytics/attendance
  - GET /api/v1/analytics/incidents
  - GET /api/v1/analytics/productivity
  - GET /api/v1/analytics/camera-coverage
  - GET /api/v1/analytics/summary

Date Filtering Capabilities & Limitations:
  - Attendance, Incidents, Productivity, and Summary support start_date and end_date.
  - Workforce Overview does NOT support date filtering because user accounts and role
    assignments in Operix are a current static snapshot.
  - Camera Coverage uses period_hours as the observation window.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class WorkforceQueryRequest(BaseModel):
    """
    Query parameters for GET /api/v1/analytics/workforce.
    NOTE: Date filtering is NOT supported for workforce overview because user accounts
    and factory memberships represent the current state snapshot.
    """
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID. If omitted, uses default configured factory.",
    )


class AttendanceQueryRequest(BaseModel):
    """
    Query parameters for GET /api/v1/analytics/attendance.
    Supports optional date filtering over incident review/resolve activity.
    """
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID.",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start timestamp in ISO 8601 UTC format (inclusive).",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End timestamp in ISO 8601 UTC format (exclusive).",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "AttendanceQueryRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self


class IncidentQueryRequest(BaseModel):
    """
    Query parameters for GET /api/v1/analytics/incidents.
    Supports date filtering over incident opened_at timestamps.
    """
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID.",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start timestamp in ISO 8601 UTC format (inclusive).",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End timestamp in ISO 8601 UTC format (exclusive).",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "IncidentQueryRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self


class ProductivityQueryRequest(BaseModel):
    """
    Query parameters for GET /api/v1/analytics/productivity.
    Supports date filtering and configurable performance thresholds.
    """
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID.",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start timestamp in ISO 8601 UTC format.",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End timestamp in ISO 8601 UTC format.",
    )
    low_threshold: Optional[int] = Field(
        default=None,
        ge=0,
        description="Threshold below which worker is labeled 'low' (default: 2).",
    )
    high_threshold: Optional[int] = Field(
        default=None,
        ge=0,
        description="Threshold at or above which worker is labeled 'high' (default: 5).",
    )

    @model_validator(mode="after")
    def validate_inputs(self) -> "ProductivityQueryRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        if (
            self.low_threshold is not None
            and self.high_threshold is not None
            and self.low_threshold > self.high_threshold
        ):
            raise ValueError("low_threshold cannot exceed high_threshold")
        return self


class CameraCoverageQueryRequest(BaseModel):
    """
    Query parameters for GET /api/v1/analytics/camera-coverage.
    NOTE: Uses period_hours as the observation window for coverage calculations.
    """
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID.",
    )
    period_hours: float = Field(
        default=720.0,
        gt=0,
        description="Observation window in hours (default: 720.0 = 30 days).",
    )


class SummaryQueryRequest(BaseModel):
    """
    Query parameters for GET /api/v1/analytics/summary.
    Consolidates parameters across all workforce analytics operations.
    """
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID.",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start timestamp in ISO 8601 UTC format for incident and attendance metrics.",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End timestamp in ISO 8601 UTC format.",
    )
    period_hours: float = Field(
        default=720.0,
        gt=0,
        description="Observation window in hours for camera coverage metrics (default: 720.0).",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "SummaryQueryRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self
