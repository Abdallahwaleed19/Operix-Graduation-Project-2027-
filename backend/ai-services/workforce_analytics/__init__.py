"""
workforce_analytics/__init__.py
Operix Workforce Analytics package.
"""
from .analytics import (
    get_workforce_overview,
    calculate_attendance_metrics,
    calculate_incident_analytics,
    calculate_productivity_metrics,
    calculate_camera_coverage,
    generate_workforce_summary,
)

__all__ = [
    "get_workforce_overview",
    "calculate_attendance_metrics",
    "calculate_incident_analytics",
    "calculate_productivity_metrics",
    "calculate_camera_coverage",
    "generate_workforce_summary",
]
