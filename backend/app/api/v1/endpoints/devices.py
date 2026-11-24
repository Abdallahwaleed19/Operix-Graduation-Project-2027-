"""
app/api/v1/endpoints/devices.py
REST API endpoints for tenant-safe Camera and Sensor management.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ....core.database import get_db, set_tenant_context
from ....core.security import AuthorizationException
from ....models.enums import SourceStatus
from ....schemas.common import APIResponse, APIResponseMeta
from ....schemas.devices import (
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraUpdate,
    SensorCreate,
    SensorListResponse,
    SensorReadingListResponse,
    SensorReadingResponse,
    SensorResponse,
    SensorUpdate,
)
from ....services.device_service import DeviceService
from ...deps import AuthenticatedUser, get_current_user_context

router = APIRouter(prefix="/devices", tags=["Devices (Cameras & Sensors)"])

_DEVICE_ADMIN_ROLES = frozenset({"safety_supervisor", "factory_manager", "factory_admin", "platform_admin"})


def _require_device_writer(user: AuthenticatedUser) -> None:
    if user.role.strip().lower() not in _DEVICE_ADMIN_ROLES:
        raise AuthorizationException(
            "Insufficient permissions to manage devices.",
            error_code="INSUFFICIENT_PERMISSIONS",
        )


def _get_scoped_db(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
) -> Session:
    set_tenant_context(db, factory_id=user.factory_id, user_id=user.user_id)
    return db


# ── Cameras ───────────────────────────────────────────────────────────────────

@router.get(
    "/cameras",
    response_model=APIResponse[CameraListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Cameras",
)
def list_cameras(
    status_filter: Optional[SourceStatus] = Query(default=None, alias="status"),
    is_active: Optional[bool] = Query(default=None),
    department_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[CameraListResponse]:
    items, total = DeviceService.list_cameras(
        db=db,
        factory_id=user.factory_id,
        status_filter=status_filter,
        is_active=is_active,
        department_id=department_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        status="success",
        data=CameraListResponse(items=[CameraResponse.model_validate(c) for c in items], total=total),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/cameras/{camera_id}",
    response_model=APIResponse[CameraResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Camera Details",
)
def get_camera(
    camera_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[CameraResponse]:
    cam = DeviceService.get_camera(db, user.factory_id, camera_id)
    return APIResponse(
        status="success",
        data=CameraResponse.model_validate(cam),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "/cameras",
    response_model=APIResponse[CameraResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Camera",
)
def create_camera(
    cam_in: CameraCreate,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[CameraResponse]:
    _require_device_writer(user)
    cam = DeviceService.create_camera(db, user.factory_id, cam_in)
    return APIResponse(
        status="success",
        data=CameraResponse.model_validate(cam),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/cameras/{camera_id}",
    response_model=APIResponse[CameraResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Camera Configuration",
)
def update_camera(
    camera_id: uuid.UUID,
    cam_in: CameraUpdate,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[CameraResponse]:
    _require_device_writer(user)
    cam = DeviceService.update_camera(db, user.factory_id, camera_id, cam_in)
    return APIResponse(
        status="success",
        data=CameraResponse.model_validate(cam),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "/cameras/{camera_id}/toggle",
    response_model=APIResponse[CameraResponse],
    status_code=status.HTTP_200_OK,
    summary="Enable or Disable Camera",
)
def toggle_camera(
    camera_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[CameraResponse]:
    _require_device_writer(user)
    cam = DeviceService.toggle_camera(db, user.factory_id, camera_id)
    return APIResponse(
        status="success",
        data=CameraResponse.model_validate(cam),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


# ── Sensors ───────────────────────────────────────────────────────────────────

@router.get(
    "/sensors",
    response_model=APIResponse[SensorListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Sensors",
)
def list_sensors(
    status_filter: Optional[SourceStatus] = Query(default=None, alias="status"),
    is_active: Optional[bool] = Query(default=None),
    department_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[SensorListResponse]:
    items, total = DeviceService.list_sensors(
        db=db,
        factory_id=user.factory_id,
        status_filter=status_filter,
        is_active=is_active,
        department_id=department_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        status="success",
        data=SensorListResponse(items=[SensorResponse.model_validate(s) for s in items], total=total),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/sensors/{sensor_id}",
    response_model=APIResponse[SensorResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Sensor Details",
)
def get_sensor(
    sensor_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[SensorResponse]:
    sensor = DeviceService.get_sensor(db, user.factory_id, sensor_id)
    return APIResponse(
        status="success",
        data=SensorResponse.model_validate(sensor),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "/sensors",
    response_model=APIResponse[SensorResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Sensor",
)
def create_sensor(
    sensor_in: SensorCreate,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[SensorResponse]:
    _require_device_writer(user)
    sensor = DeviceService.create_sensor(db, user.factory_id, sensor_in)
    return APIResponse(
        status="success",
        data=SensorResponse.model_validate(sensor),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/sensors/{sensor_id}",
    response_model=APIResponse[SensorResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Sensor Configuration",
)
def update_sensor(
    sensor_id: uuid.UUID,
    sensor_in: SensorUpdate,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[SensorResponse]:
    _require_device_writer(user)
    sensor = DeviceService.update_sensor(db, user.factory_id, sensor_id, sensor_in)
    return APIResponse(
        status="success",
        data=SensorResponse.model_validate(sensor),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "/sensors/{sensor_id}/toggle",
    response_model=APIResponse[SensorResponse],
    status_code=status.HTTP_200_OK,
    summary="Enable or Disable Sensor",
)
def toggle_sensor(
    sensor_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[SensorResponse]:
    _require_device_writer(user)
    sensor = DeviceService.toggle_sensor(db, user.factory_id, sensor_id)
    return APIResponse(
        status="success",
        data=SensorResponse.model_validate(sensor),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/sensors/{sensor_id}/readings",
    response_model=APIResponse[SensorReadingListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Sensor Readings",
)
def list_sensor_readings(
    sensor_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[SensorReadingListResponse]:
    items, total = DeviceService.list_sensor_readings(
        db=db,
        factory_id=user.factory_id,
        sensor_id=sensor_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        status="success",
        data=SensorReadingListResponse(
            items=[SensorReadingResponse.model_validate(r) for r in items],
            total=total,
        ),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
