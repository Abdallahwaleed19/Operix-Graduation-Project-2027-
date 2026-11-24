"""
app/services/device_service.py
Business logic for tenant-scoped Camera, Sensor, and SensorReading operations.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.errors import OperixException, ResourceNotFoundException
from ..models.enums import SourceStatus
from ..models.operational import Camera, Department, Sensor, SensorReading
from ..schemas.devices import CameraCreate, CameraUpdate, SensorCreate, SensorUpdate


class DeviceService:
    """Caller owns DB session commit/rollback."""

    @staticmethod
    def _validate_department(db: Session, factory_id: uuid.UUID, department_id: Optional[uuid.UUID]) -> None:
        if department_id is None:
            return
        dept = db.execute(
            select(Department).where(
                Department.factory_id == factory_id,
                Department.id == department_id,
            )
        ).scalar_one_or_none()
        if dept is None:
            raise ResourceNotFoundException("Department", department_id)

    # ── Cameras ───────────────────────────────────────────────────────────────

    @staticmethod
    def list_cameras(
        db: Session,
        factory_id: uuid.UUID,
        status_filter: Optional[SourceStatus] = None,
        is_active: Optional[bool] = None,
        department_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Camera], int]:
        filters = [Camera.factory_id == factory_id]
        if status_filter is not None:
            filters.append(Camera.status == status_filter)
        if is_active is not None:
            filters.append(Camera.is_active == is_active)
        if department_id is not None:
            filters.append(Camera.department_id == department_id)

        total = db.execute(select(func.count()).select_from(Camera).where(*filters)).scalar_one()
        items = (
            db.execute(select(Camera).where(*filters).order_by(Camera.name.asc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )
        return list(items), int(total)

    @staticmethod
    def get_camera(db: Session, factory_id: uuid.UUID, camera_id: uuid.UUID) -> Camera:
        cam = db.execute(
            select(Camera).where(Camera.factory_id == factory_id, Camera.id == camera_id)
        ).scalar_one_or_none()
        if cam is None:
            raise ResourceNotFoundException("Camera", camera_id)
        return cam

    @staticmethod
    def create_camera(db: Session, factory_id: uuid.UUID, cam_in: CameraCreate) -> Camera:
        DeviceService._validate_department(db, factory_id, cam_in.department_id)
        now = datetime.now(timezone.utc)
        cam = Camera(
            factory_id=factory_id,
            department_id=cam_in.department_id,
            name=cam_in.name.strip(),
            camera_type=cam_in.camera_type,
            location_label=cam_in.location_label,
            stream_url_ref=cam_in.stream_url_ref,
            status=SourceStatus.CONFIGURED if cam_in.is_active else SourceStatus.UNAVAILABLE,
            status_since=now,
            is_active=cam_in.is_active,
        )
        db.add(cam)
        try:
            db.flush()
        except IntegrityError as exc:
            raise OperixException(
                message=f"Camera with name '{cam_in.name}' already exists in this factory.",
                status_code=409,
                error_code="DUPLICATE_DEVICE_NAME",
            ) from exc
        db.refresh(cam)
        return cam

    @staticmethod
    def update_camera(
        db: Session,
        factory_id: uuid.UUID,
        camera_id: uuid.UUID,
        cam_in: CameraUpdate,
    ) -> Camera:
        cam = DeviceService.get_camera(db, factory_id, camera_id)
        updates = cam_in.model_dump(exclude_unset=True)
        if "department_id" in updates:
            DeviceService._validate_department(db, factory_id, updates["department_id"])
        for field, value in updates.items():
            if field == "status" and value != cam.status:
                cam.status_since = datetime.now(timezone.utc)
            setattr(cam, field, value)
        try:
            db.flush()
        except IntegrityError as exc:
            raise OperixException(
                message="Camera update conflicts with an existing camera name.",
                status_code=409,
                error_code="DUPLICATE_DEVICE_NAME",
            ) from exc
        db.refresh(cam)
        return cam

    @staticmethod
    def toggle_camera(db: Session, factory_id: uuid.UUID, camera_id: uuid.UUID) -> Camera:
        cam = DeviceService.get_camera(db, factory_id, camera_id)
        cam.is_active = not cam.is_active
        cam.status = SourceStatus.AVAILABLE if cam.is_active else SourceStatus.UNAVAILABLE
        cam.status_since = datetime.now(timezone.utc)
        db.flush()
        db.refresh(cam)
        return cam

    # ── Sensors ───────────────────────────────────────────────────────────────

    @staticmethod
    def list_sensors(
        db: Session,
        factory_id: uuid.UUID,
        status_filter: Optional[SourceStatus] = None,
        is_active: Optional[bool] = None,
        department_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Sensor], int]:
        filters = [Sensor.factory_id == factory_id]
        if status_filter is not None:
            filters.append(Sensor.status == status_filter)
        if is_active is not None:
            filters.append(Sensor.is_active == is_active)
        if department_id is not None:
            filters.append(Sensor.department_id == department_id)

        total = db.execute(select(func.count()).select_from(Sensor).where(*filters)).scalar_one()
        items = (
            db.execute(select(Sensor).where(*filters).order_by(Sensor.name.asc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )
        return list(items), int(total)

    @staticmethod
    def get_sensor(db: Session, factory_id: uuid.UUID, sensor_id: uuid.UUID) -> Sensor:
        sensor = db.execute(
            select(Sensor).where(Sensor.factory_id == factory_id, Sensor.id == sensor_id)
        ).scalar_one_or_none()
        if sensor is None:
            raise ResourceNotFoundException("Sensor", sensor_id)
        return sensor

    @staticmethod
    def create_sensor(db: Session, factory_id: uuid.UUID, sensor_in: SensorCreate) -> Sensor:
        DeviceService._validate_department(db, factory_id, sensor_in.department_id)
        now = datetime.now(timezone.utc)
        sensor = Sensor(
            factory_id=factory_id,
            department_id=sensor_in.department_id,
            name=sensor_in.name.strip(),
            sensor_type=sensor_in.sensor_type,
            unit=sensor_in.unit,
            location_label=sensor_in.location_label,
            sampling_interval_s=sensor_in.sampling_interval_s,
            status=SourceStatus.CONFIGURED if sensor_in.is_active else SourceStatus.UNAVAILABLE,
            status_since=now,
            is_active=sensor_in.is_active,
        )
        db.add(sensor)
        try:
            db.flush()
        except IntegrityError as exc:
            raise OperixException(
                message=f"Sensor with name '{sensor_in.name}' already exists in this factory.",
                status_code=409,
                error_code="DUPLICATE_DEVICE_NAME",
            ) from exc
        db.refresh(sensor)
        return sensor

    @staticmethod
    def update_sensor(
        db: Session,
        factory_id: uuid.UUID,
        sensor_id: uuid.UUID,
        sensor_in: SensorUpdate,
    ) -> Sensor:
        sensor = DeviceService.get_sensor(db, factory_id, sensor_id)
        updates = sensor_in.model_dump(exclude_unset=True)
        if "department_id" in updates:
            DeviceService._validate_department(db, factory_id, updates["department_id"])
        for field, value in updates.items():
            if field == "status" and value != sensor.status:
                sensor.status_since = datetime.now(timezone.utc)
            setattr(sensor, field, value)
        try:
            db.flush()
        except IntegrityError as exc:
            raise OperixException(
                message="Sensor update conflicts with an existing sensor name.",
                status_code=409,
                error_code="DUPLICATE_DEVICE_NAME",
            ) from exc
        db.refresh(sensor)
        return sensor

    @staticmethod
    def toggle_sensor(db: Session, factory_id: uuid.UUID, sensor_id: uuid.UUID) -> Sensor:
        sensor = DeviceService.get_sensor(db, factory_id, sensor_id)
        sensor.is_active = not sensor.is_active
        sensor.status = SourceStatus.AVAILABLE if sensor.is_active else SourceStatus.UNAVAILABLE
        sensor.status_since = datetime.now(timezone.utc)
        db.flush()
        db.refresh(sensor)
        return sensor

    @staticmethod
    def list_sensor_readings(
        db: Session,
        factory_id: uuid.UUID,
        sensor_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SensorReading], int]:
        DeviceService.get_sensor(db, factory_id, sensor_id)
        filters = [SensorReading.factory_id == factory_id, SensorReading.sensor_id == sensor_id]
        total = db.execute(select(func.count()).select_from(SensorReading).where(*filters)).scalar_one()
        items = (
            db.execute(
                select(SensorReading)
                .where(*filters)
                .order_by(SensorReading.recorded_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return list(items), int(total)
