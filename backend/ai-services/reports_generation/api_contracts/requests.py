"""
reports_generation/api_contracts/requests.py
Pydantic v2 request contracts for reports generation endpoints.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..schemas import ReportFormat, ReportType


class GenerateReportRequest(BaseModel):
    """
    POST /api/v1/reports/generate
    Request body to trigger report generation.
    """
    report_type: ReportType = Field(
        ...,
        description="Category of report: 'workforce', 'incident', 'camera_coverage', or 'comprehensive_safety'.",
        example="workforce",
    )
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Target export format: 'pdf', 'excel', or 'json'.",
        example="pdf",
    )
    factory_id: Optional[UUID] = Field(
        default=None,
        description="Target factory UUID. If omitted, uses caller's authorized default factory.",
    )
    date_from: Optional[date] = Field(
        default=None,
        description="Optional start date for filtering time-based records (YYYY-MM-DD).",
        example="2026-10-01",
    )
    date_to: Optional[date] = Field(
        default=None,
        description="Optional end date for filtering time-based records (YYYY-MM-DD).",
        example="2026-11-01",
    )


class ReportFilterParams(BaseModel):
    """
    GET /api/v1/reports
    Query parameters for listing generated reports.
    """
    factory_id: Optional[UUID] = None
    report_type: Optional[ReportType] = None
    format: Optional[ReportFormat] = None
