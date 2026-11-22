"""
app/models/incidents.py
Incidents, raw detection events, evidence files, alerts, and deliveries.
Directly maps to Operix_Core_MVP_schema.sql (lines 232-358).
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    and_,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin
from .enums import (
    AlertStatus,
    DeliveryStatus,
    EventType,
    EvidenceKind,
    IncidentState,
    NotificationChannel,
    SeverityLevel,
)


class Incident(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_incident_factory_id"),
        ForeignKeyConstraint(
            ["factory_id", "reviewed_by"],
            ["factory_memberships.factory_id", "factory_memberships.user_id"],
            name="fk_incident_reviewer",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["factory_id", "resolved_by"],
            ["factory_memberships.factory_id", "factory_memberships.user_id"],
            name="fk_incident_resolver",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "state <> 'resolved' OR resolved_at IS NOT NULL",
            name="ck_incident_resolved_has_timestamp",
        ),
        Index(
            "incidents_open_idx",
            "factory_id",
            "state",
            text("opened_at DESC"),
            postgresql_where=text("state <> 'resolved'"),
        ),
        Index(
            "incidents_time_idx",
            "factory_id",
            text("opened_at DESC"),
        ),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    incident_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type", native_enum=True),
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", native_enum=True),
        nullable=False,
    )
    state: Mapped[IncidentState] = mapped_column(
        Enum(IncidentState, name="incident_state", native_enum=True),
        nullable=False,
        default=IncidentState.DETECTED,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    events = relationship(
        "Event",
        back_populates="incident",
        foreign_keys="[Event.factory_id, Event.incident_id]",
    )
    alerts = relationship(
        "Alert",
        back_populates="incident",
        cascade="all, delete-orphan",
        foreign_keys="[Alert.factory_id, Alert.incident_id]",
    )
    reviewer = relationship(
        "FactoryMembership",
        foreign_keys="[Incident.factory_id, Incident.reviewed_by]",
        primaryjoin="and_(Incident.factory_id == FactoryMembership.factory_id, Incident.reviewed_by == FactoryMembership.user_id)",
    )
    resolver = relationship(
        "FactoryMembership",
        foreign_keys="[Incident.factory_id, Incident.resolved_by]",
        primaryjoin="and_(Incident.factory_id == FactoryMembership.factory_id, Incident.resolved_by == FactoryMembership.user_id)",
    )


class Event(Base):
    """AI or sensor detected event. ID is client/producer supplied for idempotency."""
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_event_factory_id"),
        ForeignKeyConstraint(
            ["factory_id", "camera_id"],
            ["cameras.factory_id", "cameras.id"],
            name="fk_event_camera",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["factory_id", "zone_id"],
            ["monitoring_zones.factory_id", "monitoring_zones.id"],
            name="fk_event_zone",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["factory_id", "rule_id"],
            ["safety_rules.factory_id", "safety_rules.id"],
            name="fk_event_rule",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["factory_id", "sensor_id"],
            ["sensors.factory_id", "sensors.id"],
            name="fk_event_sensor",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["factory_id", "incident_id"],
            ["incidents.factory_id", "incidents.id"],
            name="fk_event_incident",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "num_nonnulls(camera_id, sensor_id) = 1",
            name="ck_event_single_source",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_event_confidence_range",
        ),
        CheckConstraint(
            "bbox_x IS NULL OR (bbox_x >= 0 AND bbox_x <= 1)",
            name="ck_event_bbox_x",
        ),
        CheckConstraint(
            "bbox_y IS NULL OR (bbox_y >= 0 AND bbox_y <= 1)",
            name="ck_event_bbox_y",
        ),
        CheckConstraint(
            "bbox_w IS NULL OR (bbox_w >= 0 AND bbox_w <= 1)",
            name="ck_event_bbox_w",
        ),
        CheckConstraint(
            "bbox_h IS NULL OR (bbox_h >= 0 AND bbox_h <= 1)",
            name="ck_event_bbox_h",
        ),
        Index("events_time_idx", "factory_id", text("detected_at DESC")),
        Index("events_type_idx", "factory_id", "event_type", text("detected_at DESC")),
        Index(
            "events_camera_idx",
            "factory_id",
            "camera_id",
            text("detected_at DESC"),
            postgresql_where=text("camera_id IS NOT NULL"),
        ),
        Index(
            "events_incident_idx",
            "factory_id",
            "incident_id",
            postgresql_where=text("incident_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type", native_enum=True),
        nullable=False,
    )
    camera_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    sensor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    track_ref: Mapped[Optional[int]] = mapped_column(nullable=True)
    bbox_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    incident = relationship(
        "Incident",
        back_populates="events",
        foreign_keys="[Event.factory_id, Event.incident_id]",
    )
    evidence_files = relationship(
        "EvidenceFile",
        back_populates="event",
        cascade="all, delete-orphan",
        foreign_keys="[EvidenceFile.factory_id, EvidenceFile.event_id]",
    )


class EvidenceFile(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "evidence_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["factory_id", "event_id"],
            ["events.factory_id", "events.id"],
            name="fk_evidence_event",
            ondelete="CASCADE",
        ),
        CheckConstraint("size_bytes > 0", name="ck_evidence_size_positive"),
        CheckConstraint(
            "kind = 'snapshot' OR duration_s IS NOT NULL",
            name="ck_evidence_clip_duration",
        ),
        CheckConstraint(
            "storage_key LIKE 'f/' || factory_id::text || '/%'",
            name="ck_evidence_storage_key_pattern",
        ),
        Index("evidence_event_idx", "factory_id", "event_id"),
        Index(
            "evidence_expiry_idx",
            "expires_at",
            postgresql_where=text("purged_at IS NULL AND expires_at IS NOT NULL"),
        ),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    kind: Mapped[EvidenceKind] = mapped_column(
        Enum(EvidenceKind, name="evidence_kind", native_enum=True),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(60), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    purged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    event = relationship(
        "Event",
        back_populates="evidence_files",
        foreign_keys="[EvidenceFile.factory_id, EvidenceFile.event_id]",
    )


class Alert(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_alert_factory_id"),
        ForeignKeyConstraint(
            ["factory_id", "incident_id"],
            ["incidents.factory_id", "incidents.id"],
            name="fk_alert_incident",
            ondelete="CASCADE",
        ),
        Index("alerts_time_idx", "factory_id", text("created_at DESC")),
        Index("alerts_incident_idx", "factory_id", "incident_id"),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", native_enum=True),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status", native_enum=True),
        nullable=False,
        default=AlertStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    incident = relationship(
        "Incident",
        back_populates="alerts",
        foreign_keys="[Alert.factory_id, Alert.incident_id]",
    )
    deliveries = relationship(
        "AlertDelivery",
        back_populates="alert",
        cascade="all, delete-orphan",
        foreign_keys="[AlertDelivery.factory_id, AlertDelivery.alert_id]",
    )


class NotificationTarget(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "notification_targets"
    __table_args__ = (
        UniqueConstraint("factory_id", "id", name="uq_notif_target_factory_id"),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", native_enum=True),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    min_severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", native_enum=True),
        nullable=False,
        default=SeverityLevel.HIGH,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AlertDelivery(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "alert_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["factory_id", "alert_id"],
            ["alerts.factory_id", "alerts.id"],
            name="fk_delivery_alert",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["factory_id", "target_id"],
            ["notification_targets.factory_id", "notification_targets.id"],
            name="fk_delivery_target",
            ondelete="SET NULL",
        ),
        Index("alert_deliveries_alert_idx", "factory_id", "alert_id"),
        Index(
            "alert_deliveries_retry_idx",
            "status",
            "last_attempt_at",
            postgresql_where=text("status IN ('queued', 'failed')"),
        ),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        nullable=False,
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", native_enum=True),
        nullable=False,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", native_enum=True),
        nullable=False,
        default=DeliveryStatus.QUEUED,
    )
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_ref: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    alert = relationship(
        "Alert",
        back_populates="deliveries",
        foreign_keys="[AlertDelivery.factory_id, AlertDelivery.alert_id]",
    )
