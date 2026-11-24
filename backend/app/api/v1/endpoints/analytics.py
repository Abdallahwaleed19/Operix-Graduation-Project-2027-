"""
app/api/v1/endpoints/analytics.py
REST API endpoints for Workforce Analytics AI Subsystem.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ....schemas.common import APIResponse, APIResponseMeta
from ...ai_deps import get_workforce_analytics_service_dep
from ...deps import AuthenticatedUser, get_current_factory_id, get_current_user_context, get_tenant_db

router = APIRouter(prefix="/analytics", tags=["Workforce Analytics"])


@router.get(
    "/overview",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Workforce Overview Metrics",
    description="Retrieve overall workforce metrics: total workers, active/inactive split, and role distribution.",
)
def get_workforce_overview(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    svc: Any = Depends(get_workforce_analytics_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get high-level worker counts and role breakdown for the tenant factory."""
    overview = svc.get_workforce_overview(factory_id=user.factory_id, session=db, as_dict=True)
    return APIResponse(
        status="success",
        data=overview,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/attendance",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Attendance & Activity Metrics",
    description="Retrieve worker activity and attendance metrics based on incident review/resolve timestamps.",
)
def get_attendance_metrics(
    start_date: Optional[datetime] = Query(default=None, description="Start timestamp (UTC)"),
    end_date: Optional[datetime] = Query(default=None, description="End timestamp (UTC)"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    svc: Any = Depends(get_workforce_analytics_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get active worker counts and attendance proxy metrics."""
    attendance = svc.get_attendance_metrics(
        factory_id=user.factory_id,
        start_date=start_date,
        end_date=end_date,
        session=db,
        as_dict=True,
    )
    return APIResponse(
        status="success",
        data=attendance,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/incidents",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Safety Incident Analytics",
    description="Retrieve incident distributions by type, severity, and resolution status.",
)
def get_incident_analytics(
    start_date: Optional[datetime] = Query(default=None, description="Start timestamp (UTC)"),
    end_date: Optional[datetime] = Query(default=None, description="End timestamp (UTC)"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    svc: Any = Depends(get_workforce_analytics_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get safety incident aggregates and resolution times."""
    incidents = svc.get_incident_analytics(
        factory_id=user.factory_id,
        start_date=start_date,
        end_date=end_date,
        session=db,
        as_dict=True,
    )
    return APIResponse(
        status="success",
        data=incidents,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/productivity",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Worker Productivity Metrics",
    description="Retrieve worker resolution performance and categorisation.",
)
def get_productivity_metrics(
    start_date: Optional[datetime] = Query(default=None, description="Start timestamp (UTC)"),
    end_date: Optional[datetime] = Query(default=None, description="End timestamp (UTC)"),
    low_threshold: Optional[int] = Query(default=None, ge=0, description="Low productivity threshold count"),
    high_threshold: Optional[int] = Query(default=None, ge=0, description="High productivity threshold count"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    svc: Any = Depends(get_workforce_analytics_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get per-worker incident handling efficiency metrics."""
    productivity = svc.get_productivity_metrics(
        factory_id=user.factory_id,
        start_date=start_date,
        end_date=end_date,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        session=db,
        as_dict=True,
    )
    return APIResponse(
        status="success",
        data=productivity,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/camera-coverage",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Camera Coverage & Downtime",
    description="Calculate camera uptime percentages and downtime gaps.",
)
def get_camera_coverage(
    period_hours: float = Query(default=720.0, ge=1.0, le=8760.0, description="Observation window in hours"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    svc: Any = Depends(get_workforce_analytics_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get camera coverage rates and unobserved gap analysis."""
    coverage = svc.get_camera_coverage(
        factory_id=user.factory_id,
        period_hours=period_hours,
        session=db,
        as_dict=True,
    )
    return APIResponse(
        status="success",
        data=coverage,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/summary",
    response_model=APIResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Consolidated Workforce Summary",
    description="Consolidate workforce overview, attendance, incidents, and camera metrics into one dashboard view.",
)
def get_workforce_summary(
    start_date: Optional[datetime] = Query(default=None, description="Start timestamp (UTC)"),
    end_date: Optional[datetime] = Query(default=None, description="End timestamp (UTC)"),
    period_hours: float = Query(default=720.0, ge=1.0, le=8760.0, description="Camera observation window in hours"),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_tenant_db),
    svc: Any = Depends(get_workforce_analytics_service_dep),
) -> APIResponse[Dict[str, Any]]:
    """Get single unified analytics summary for dashboard cards."""
    summary = svc.get_workforce_summary(
        factory_id=user.factory_id,
        start_date=start_date,
        end_date=end_date,
        period_hours=period_hours,
        session=db,
        as_dict=True,
    )
    return APIResponse(
        status="success",
        data=summary,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
