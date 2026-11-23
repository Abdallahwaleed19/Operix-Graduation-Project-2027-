"""
reports_generation/api_contracts/responses.py
API response contracts for the Reports Generation module.

These are plain Pydantic models representing what Seif's FastAPI layer
should return for each endpoint.  No FastAPI server is instantiated here.

Endpoints:
  POST  /api/v1/reports/generate          → GenerateReportResponse
  GET   /api/v1/reports                   → ReportListResponse
  GET   /api/v1/reports/{report_id}       → GenerateReportResponse
  GET   /api/v1/reports/{report_id}/download  → ReportDownloadResponse (binary)

Example JSON for GenerateReportResponse:
  {
    "success": true,
    "message": "Report generated successfully.",
    "data": {
      "report_id": "REP-20270115-A1B2C3",
      "report_type": "workforce",
      "format": "pdf",
      "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
      "title": "Workforce Report",
      "generated_at": "2027-01-15T10:00:00+00:00",
      "date_from": "2027-01-01",
      "date_to": "2027-01-14",
      "file_name": "workforce_REP-20270115-A1B2C3.pdf",
      "file_size_bytes": 48320,
      "mime_type": "application/pdf",
      "has_proxy_metrics": true,
      "disclaimer": "DISCLAIMER: Attendance and productivity indicators ..."
    }
  }
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..schemas import ReportMetadata


class GenerateReportResponse(BaseModel):
    """
    Returned by POST /api/v1/reports/generate and GET /api/v1/reports/{report_id}.

    Wraps ReportMetadata with a standard API envelope.
    """
    success: bool = True
    message: str = "Report generated successfully."
    data: ReportMetadata

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "message": "Report generated successfully.",
            "data": {
                "report_id": "REP-20270115-A1B2C3",
                "report_type": "workforce",
                "format": "pdf",
                "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
                "title": "Workforce Report",
                "generated_at": "2027-01-15T10:00:00+00:00",
                "date_from": "2027-01-01",
                "date_to": "2027-01-14",
                "file_name": "workforce_REP-20270115-A1B2C3.pdf",
                "file_size_bytes": 48320,
                "mime_type": "application/pdf",
                "has_proxy_metrics": True,
            }
        }
    }}


class ReportListResponse(BaseModel):
    """
    Returned by GET /api/v1/reports.

    Provides a paginated list of previously generated report metadata.
    Note: The current implementation stores reports on disk only;
    this response is built by scanning the reports storage directory.
    """
    success: bool = True
    total: int = Field(description="Total number of reports available.")
    page: int = Field(default=1, description="Current page number (1-indexed).")
    page_size: int = Field(default=20, description="Number of items per page.")
    data: List[ReportMetadata]

    model_config = {"json_schema_extra": {
        "example": {
            "success": True,
            "total": 2,
            "page": 1,
            "page_size": 20,
            "data": [
                {
                    "report_id": "REP-20270115-A1B2C3",
                    "report_type": "workforce",
                    "format": "pdf",
                    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
                    "title": "Workforce Report",
                    "generated_at": "2027-01-15T10:00:00+00:00",
                    "file_name": "workforce_REP-20270115-A1B2C3.pdf",
                    "file_size_bytes": 48320,
                    "mime_type": "application/pdf",
                    "has_proxy_metrics": True,
                }
            ]
        }
    }}


class ReportDownloadResponse(BaseModel):
    """
    Metadata for GET /api/v1/reports/{report_id}/download.

    The FastAPI integration layer should read `file_path` and stream
    the binary file to the client using `FileResponse` with `media_type`
    set to `mime_type`.

    The actual file bytes are NOT embedded here — this model carries
    only the metadata Seif needs to build the streaming response.
    """
    report_id: str
    file_name: str
    file_path: str = Field(description="Absolute path to the report file on disk.")
    mime_type: str
    file_size_bytes: int

    model_config = {"json_schema_extra": {
        "example": {
            "report_id": "REP-20270115-A1B2C3",
            "file_name": "workforce_REP-20270115-A1B2C3.pdf",
            "file_path": "/app/storage/reports/workforce_REP-20270115-A1B2C3.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 48320,
        }
    }}


class ErrorResponse(BaseModel):
    """Standard error envelope returned on API failures."""
    success: bool = False
    error_code: str
    message: str
    detail: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "success": False,
            "error_code": "INVALID_REPORT_TYPE",
            "message": "Unsupported report type: 'xyz'.",
            "detail": None,
        }
    }}
