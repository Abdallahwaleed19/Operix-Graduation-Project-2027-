"""
app/api/v1/endpoints/incidents.py
REST API endpoints for tenant-safe Incident Management.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from ....core.database import get_db, set_tenant_context
from ....core.security import AuthorizationException
from ....models.enums import EventType, IncidentState, SeverityLevel
from ....schemas.common import APIResponse, APIResponseMeta
from ....schemas.incidents import (
    IncidentCreate,
    IncidentListResponse,
    IncidentResolveRequest,
    IncidentResponse,
    IncidentUpdate,
)
from ....services.incident_service import IncidentService
from ...deps import AuthenticatedUser, get_current_user_context

router = APIRouter(prefix="/incidents", tags=["Incidents Management"])

_PRIVILEGED_ROLES = frozenset({"safety_supervisor", "factory_manager", "factory_admin", "platform_admin"})


def _require_incident_writer(user: AuthenticatedUser) -> None:
    if user.role.strip().lower() not in _PRIVILEGED_ROLES:
        raise AuthorizationException(
            "Insufficient permissions to modify incidents.",
            error_code="INSUFFICIENT_PERMISSIONS",
        )


def _get_scoped_db(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
) -> Session:
    set_tenant_context(db, factory_id=user.factory_id, user_id=user.user_id)
    return db


@router.get(
    "",
    response_model=APIResponse[IncidentListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Incidents",
)
def list_incidents(
    state: Optional[IncidentState] = Query(default=None),
    severity: Optional[SeverityLevel] = Query(default=None),
    incident_type: Optional[EventType] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[IncidentListResponse]:
    items, total = IncidentService.list_incidents(
        db=db,
        factory_id=user.factory_id,
        state=state,
        severity=severity,
        incident_type=incident_type,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        status="success",
        data=IncidentListResponse(
            items=[IncidentResponse.model_validate(i) for i in items],
            total=total,
        ),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{incident_id}",
    response_model=APIResponse[IncidentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Incident Details",
)
def get_incident(
    incident_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[IncidentResponse]:
    incident = IncidentService.get_incident(db=db, factory_id=user.factory_id, incident_id=incident_id)
    return APIResponse(
        status="success",
        data=IncidentResponse.model_validate(incident),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "",
    response_model=APIResponse[IncidentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Manual Incident",
)
def create_incident(
    incident_in: IncidentCreate,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[IncidentResponse]:
    _require_incident_writer(user)
    incident, payload = IncidentService.create_incident(
        db=db,
        factory_id=user.factory_id,
        incident_in=incident_in,
    )
    db.commit()
    background_tasks.add_task(IncidentService.broadcast_event, user.factory_id, payload)
    return APIResponse(
        status="success",
        data=IncidentResponse.model_validate(incident),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/{incident_id}",
    response_model=APIResponse[IncidentResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Incident",
)
def update_incident(
    incident_id: uuid.UUID,
    incident_in: IncidentUpdate,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[IncidentResponse]:
    _require_incident_writer(user)
    incident = IncidentService.update_incident(
        db=db,
        factory_id=user.factory_id,
        incident_id=incident_id,
        incident_in=incident_in,
    )
    return APIResponse(
        status="success",
        data=IncidentResponse.model_validate(incident),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/{incident_id}/acknowledge",
    response_model=APIResponse[IncidentResponse],
    status_code=status.HTTP_200_OK,
    summary="Acknowledge Incident",
)
def acknowledge_incident(
    incident_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[IncidentResponse]:
    _require_incident_writer(user)
    incident, payload = IncidentService.acknowledge_incident(
        db=db,
        factory_id=user.factory_id,
        user_id=user.user_id,
        incident_id=incident_id,
    )
    db.commit()
    background_tasks.add_task(IncidentService.broadcast_event, user.factory_id, payload)
    return APIResponse(
        status="success",
        data=IncidentResponse.model_validate(incident),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/{incident_id}/resolve",
    response_model=APIResponse[IncidentResponse],
    status_code=status.HTTP_200_OK,
    summary="Resolve Incident",
)
def resolve_incident(
    incident_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    body: Optional[IncidentResolveRequest] = None,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[IncidentResponse]:
    _require_incident_writer(user)
    note = body.resolution_note if body is not None else None
    incident, payload = IncidentService.resolve_incident(
        db=db,
        factory_id=user.factory_id,
        user_id=user.user_id,
        incident_id=incident_id,
        resolution_note=note,
    )
    db.commit()
    background_tasks.add_task(IncidentService.broadcast_event, user.factory_id, payload)
    return APIResponse(
        status="success",
        data=IncidentResponse.model_validate(incident),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
