"""
app/models/__init__.py
Registry of all Operix SQLAlchemy models.
"""
from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import (
    AlertStatus,
    CameraType,
    DeliveryStatus,
    EventType,
    EvidenceKind,
    FactoryStatus,
    GapReason,
    IncidentState,
    NotificationChannel,
    SensorType,
    SeverityLevel,
    SourceStatus,
    TokenPurpose,
    UserStatus,
    ZoneType,
)
from .incidents import Alert, AlertDelivery, Event, EvidenceFile, Incident, NotificationTarget
from .operational import Camera, Department, MonitoringZone, SafetyRule, Sensor, SensorReading, UnobservedGap
from .tenant import AuthToken, Factory, FactoryMembership, Permission, Role, RolePermission, User

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Enums
    "FactoryStatus",
    "UserStatus",
    "TokenPurpose",
    "CameraType",
    "SensorType",
    "SourceStatus",
    "ZoneType",
    "EventType",
    "SeverityLevel",
    "IncidentState",
    "EvidenceKind",
    "AlertStatus",
    "NotificationChannel",
    "DeliveryStatus",
    "GapReason",
    # Tenant Models
    "Factory",
    "User",
    "AuthToken",
    "Role",
    "Permission",
    "RolePermission",
    "FactoryMembership",
    # Operational Models
    "Department",
    "Camera",
    "Sensor",
    "MonitoringZone",
    "SafetyRule",
    "UnobservedGap",
    "SensorReading",
    # Incidents & Alerts Models
    "Incident",
    "Event",
    "EvidenceFile",
    "Alert",
    "NotificationTarget",
    "AlertDelivery",
]
