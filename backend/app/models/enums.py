"""
app/models/enums.py
Enumerations matching Mohamed Salah's PostgreSQL DDL ENUM types.
"""
from enum import Enum


class FactoryStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class UserStatus(str, Enum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class TokenPurpose(str, Enum):
    ACTIVATION = "activation"
    PASSWORD_RESET = "password_reset"
    REFRESH = "refresh"


class CameraType(str, Enum):
    CCTV = "cctv"
    THERMAL = "thermal"


class SensorType(str, Enum):
    TEMPERATURE = "temperature"


class SourceStatus(str, Enum):
    CONFIGURED = "configured"
    CONNECTING = "connecting"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RECOVERING = "recovering"


class ZoneType(str, Enum):
    RESTRICTED = "restricted"
    PPE_REQUIRED = "ppe_required"
    MONITORED = "monitored"


class EventType(str, Enum):
    PPE_VIOLATION = "ppe_violation"
    FALL = "fall"
    RESTRICTED_ZONE_INTRUSION = "restricted_zone_intrusion"
    POTENTIAL_FATIGUE = "potential_fatigue"
    FIRE = "fire"
    SMOKE = "smoke"
    TEMPERATURE_ANOMALY = "temperature_anomaly"
    SOURCE_FAILURE = "source_failure"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentState(str, Enum):
    DETECTED = "detected"
    CLASSIFIED = "classified"
    RECORDED = "recorded"
    ALERT_PENDING = "alert_pending"
    ALERT_DISPATCHED = "alert_dispatched"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"


class EvidenceKind(str, Enum):
    SNAPSHOT = "snapshot"
    CLIP = "clip"


class AlertStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    DASHBOARD = "dashboard"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class DeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    ABANDONED = "abandoned"


class GapReason(str, Enum):
    STREAM_LOST = "stream_lost"
    CAMERA_BLOCKED = "camera_blocked"
    POOR_QUALITY = "poor_quality"
    OTHER = "other"
