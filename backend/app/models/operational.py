"""
app/models/operational.py
Operational resources: departments, cameras, sensors, zones, safety rules, gaps, and readings.
Directly maps to Operix_Core_MVP_schema.sql (lines 108-230).
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import CameraType, EventType, GapReason, SensorType, SeverityLevel, SourceStatus, ZoneType


class Department(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_department_factory_id"),
        UniqueConstraint("factory_id", "name", name="uq_department_factory_name"),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    cameras = relationship(
        "Camera",
        back_populates="department",
        foreign_keys="[Camera.factory_id, Camera.department_id]",
    )
    sensors = relationship(
        "Sensor",
        back_populates="department",
        foreign_keys="[Sensor.factory_id, Sensor.department_id]",
    )


class Camera(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cameras"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_camera_factory_id"),
        UniqueConstraint("factory_id", "name", name="uq_camera_factory_name"),
        ForeignKeyConstraint(
            ["factory_id", "department_id"],
            ["departments.factory_id", "departments.id"],
            name="fk_camera_department",
            ondelete="SET NULL",
        ),
        Index("cameras_status_idx", "factory_id", "status"),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    camera_type: Mapped[CameraType] = mapped_column(
        Enum(CameraType, name="camera_type", native_enum=True),
        nullable=False,
        default=CameraType.CCTV,
    )
    location_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    stream_url_ref: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status", native_enum=True),
        nullable=False,
        default=SourceStatus.CONFIGURED,
    )
    status_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    department = relationship(
        "Department",
        back_populates="cameras",
        foreign_keys="[Camera.factory_id, Camera.department_id]",
    )
    zones = relationship(
        "MonitoringZone",
        back_populates="camera",
        cascade="all, delete-orphan",
        foreign_keys="[MonitoringZone.factory_id, MonitoringZone.camera_id]",
    )
    gaps = relationship(
        "UnobservedGap",
        back_populates="camera",
        cascade="all, delete-orphan",
        foreign_keys="[UnobservedGap.factory_id, UnobservedGap.camera_id]",
    )


class Sensor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sensors"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_sensor_factory_id"),
        UniqueConstraint("factory_id", "name", name="uq_sensor_factory_name"),
        ForeignKeyConstraint(
            ["factory_id", "department_id"],
            ["departments.factory_id", "departments.id"],
            name="fk_sensor_department",
            ondelete="SET NULL",
        ),
        CheckConstraint("sampling_interval_s > 0", name="ck_sensor_sampling_interval"),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(
        Enum(SensorType, name="sensor_type", native_enum=True),
        nullable=False,
        default=SensorType.TEMPERATURE,
    )
    unit: Mapped[str] = mapped_column(String(8), nullable=False, default="C")
    location_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sampling_interval_s: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    device_key_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, name="source_status", native_enum=True),
        nullable=False,
        default=SourceStatus.CONFIGURED,
    )
    status_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    department = relationship(
        "Department",
        back_populates="sensors",
        foreign_keys="[Sensor.factory_id, Sensor.department_id]",
    )


class MonitoringZone(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "monitoring_zones"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_zone_factory_id"),
        ForeignKeyConstraint(
            ["factory_id", "camera_id"],
            ["cameras.factory_id", "cameras.id"],
            name="fk_zone_camera",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["factory_id", "department_id"],
            ["departments.factory_id", "departments.id"],
            name="fk_zone_department",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "jsonb_typeof(polygon) = 'array' AND jsonb_array_length(polygon) >= 3",
            name="ck_monitoring_zone_polygon",
        ),
        Index(
            "monitoring_zones_camera_idx",
            "factory_id",
            "camera_id",
            postgresql_where=text("is_active IS TRUE"),
        ),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(
        Enum(ZoneType, name="zone_type", native_enum=True),
        nullable=False,
    )
    polygon: Mapped[List[Any]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    camera = relationship(
        "Camera",
        back_populates="zones",
        foreign_keys="[MonitoringZone.factory_id, MonitoringZone.camera_id]",
    )


class SafetyRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "safety_rules"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_rule_factory_id"),
        ForeignKeyConstraint(
            ["factory_id", "zone_id"],
            ["monitoring_zones.factory_id", "monitoring_zones.id"],
            name="fk_rule_zone",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["factory_id", "department_id"],
            ["departments.factory_id", "departments.id"],
            name="fk_rule_department",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["factory_id", "sensor_id"],
            ["sensors.factory_id", "sensors.id"],
            name="fk_rule_sensor",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "min_confidence IS NULL OR (min_confidence >= 0 AND min_confidence <= 1)",
            name="ck_rule_min_confidence",
        ),
        CheckConstraint(
            "min_duration_s IS NULL OR min_duration_s >= 0",
            name="ck_rule_min_duration",
        ),
        CheckConstraint(
            "num_nonnulls(zone_id, department_id, sensor_id) <= 1",
            name="ck_rule_scope_exclusivity",
        ),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type", native_enum=True),
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", native_enum=True),
        nullable=False,
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    sensor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    min_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_duration_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    threshold_value: Mapped[Optional[float]] = mapped_column(Numeric(8, 3), nullable=True)
    notify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class UnobservedGap(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "unobserved_gaps"
    __table_args__ = (
        ForeignKeyConstraint(
            ["factory_id", "camera_id"],
            ["cameras.factory_id", "cameras.id"],
            name="fk_gap_camera",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_gap_ended_after_started",
        ),
        Index(
            "unobserved_gaps_camera_idx",
            "factory_id",
            "camera_id",
            text("started_at DESC"),
        ),
        Index(
            "unobserved_gaps_one_open",
            "camera_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[GapReason] = mapped_column(
        Enum(GapReason, name="gap_reason", native_enum=True),
        nullable=False,
        default=GapReason.STREAM_LOST,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    camera = relationship(
        "Camera",
        back_populates="gaps",
        foreign_keys="[UnobservedGap.factory_id, UnobservedGap.camera_id]",
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["factory_id", "sensor_id"],
            ["sensors.factory_id", "sensors.id"],
            name="fk_reading_sensor",
            ondelete="CASCADE",
        ),
        {"postgresql_partition_by": "RANGE (recorded_at)"},
    )

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
    )
    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
