"""
reports_generation/exceptions.py
Domain exceptions for reports generation.
"""
from __future__ import annotations


class ReportBaseException(Exception):
    """Base exception for reports generation module."""
    pass


class InvalidReportTypeError(ReportBaseException):
    """Raised when an unknown or unsupported report type is requested."""
    pass


class InvalidReportFormatError(ReportBaseException):
    """Raised when an unsupported export format is requested."""
    pass


class InvalidDateRangeError(ReportBaseException):
    """Raised when start_date is after end_date or exceeds max span."""
    pass


class ReportDataExtractionError(ReportBaseException):
    """Raised when underlying data extraction fails."""
    pass


class ReportExportError(ReportBaseException):
    """Raised when rendering to PDF, Excel, or file storage fails."""
    pass


class ReportNotFoundError(ReportBaseException):
    """Raised when looking up a report artifact that does not exist."""
    pass
