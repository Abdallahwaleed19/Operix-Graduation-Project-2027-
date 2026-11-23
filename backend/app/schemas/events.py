"""
app/schemas/events.py
Pydantic validation schemas for Computer Vision event ingestion,
matching the verified Operix CV event contract (CV Team Guide §6).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import EventType


# Mapping from Computer Vision event_type strings to Database EventType enum
CV_TO_DB_EVENT_TYPE: Dict[str, EventType] = {
    # PPE Detection module
    "ppe_violation": EventType.PPE_VIOLATION,
    # Fall Detection module
    "potential_fall": EventType.FALL,
    "fall": EventType.FALL,
    # Person Tracking & Zone module
    "restricted_zone_entry": EventType.RESTRICTED_ZONE_INTRUSION,
    "restricted_zone_intrusion": EventType.RESTRICTED_ZONE_INTRUSION,
    "restricted_zone_exit": EventType.RESTRICTED_ZONE_INTRUSION,
    "potential_fatigue": EventType.POTENTIAL_FATIGUE,
    "fire": EventType.FIRE,
    "smoke": EventType.SMOKE,
    "temperature_anomaly": EventType.TEMPERATURE_ANOMALY,
    "source_failure": EventType.SOURCE_FAILURE,
}


class CVDetection(BaseModel):
    """Single per-frame detection item from CV model."""
    label: str = Field(..., description="Detected class label (e.g. person, helmet, safety_vest)")
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="[x1, y1, x2, y2] in pixels")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    track_id: Optional[int] = Field(None, description="Local tracker ID")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class CVEventIngest(BaseModel):
    """
    Direct mapping to CV Guide §6.1 / §6.7 Event specification.
    Sent by CV pipeline when a safety rule condition is confirmed.
    """
    event_id: uuid.UUID = Field(..., description="UUIDv4 supplied by producer for idempotency")
    event_type: str = Field(..., description="CV event type (e.g. ppe_violation, potential_fall, restricted_zone_entry)")
    event_state: str = Field(default="started", description="'started', 'ongoing', or 'ended'")
    module: str = Field(..., description="Originating module (e.g. ppe_detection, fall_detection, person_tracking)")
    camera_id: str = Field(..., description="Camera identifier (UUID or camera string tag)")
    timestamp: datetime = Field(..., description="Detection timestamp (ISO 8601 UTC)")
    frame_index: Optional[int] = Field(None, ge=0, description="Video frame sequence index")
    frame_size: Optional[List[int]] = Field(
        None,
        min_length=2,
        max_length=2,
        description="Frame dimensions [width, height] for coordinate normalization",
    )
    bbox: Optional[List[float]] = Field(
        None,
        min_length=4,
        max_length=4,
        description="Bounding box [x1, y1, x2, y2] in original pixels",
    )
    track_id: Optional[int] = Field(None, description="Transient tracker reference ID")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Rule/detector confidence")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Module-specific details")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in CV_TO_DB_EVENT_TYPE:
            allowed = list(CV_TO_DB_EVENT_TYPE.keys())
            raise ValueError(f"Unknown event_type '{v}'. Allowed: {allowed}")
        return clean

    @field_validator("event_state")
    @classmethod
    def validate_event_state(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("started", "ongoing", "ended"):
            raise ValueError("event_state must be 'started', 'ongoing', or 'ended'")
        return clean


class CVFrameResultIngest(BaseModel):
    """
    Container representing FrameResult from CV pipeline (§6.1).
    Allows ingestion of multi-event frame batches.
    """
    schema_version: str = Field(default="1.0")
    module: str
    camera_id: str
    frame_index: int = Field(..., ge=0)
    timestamp: datetime
    frame_size: List[int] = Field(..., min_length=2, max_length=2)
    detections: List[CVDetection] = Field(default_factory=list)
    events: List[CVEventIngest] = Field(default_factory=list)


class EventResponse(BaseModel):
    """Normalized event record representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    factory_id: uuid.UUID
    event_type: EventType
    camera_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None
    rule_id: Optional[uuid.UUID] = None
    sensor_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    detected_at: datetime
    ingested_at: datetime
    confidence: Optional[float] = None
    track_ref: Optional[int] = None
    bbox_x: Optional[float] = None
    bbox_y: Optional[float] = None
    bbox_w: Optional[float] = None
    bbox_h: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class EventIngestResponse(BaseModel):
    """API response after ingesting a single CV event."""
    event_id: uuid.UUID
    status: str = Field(..., description="'ingested' or 'duplicate_ignored'")
    event_type: str
    broadcast: bool = Field(True, description="Whether event was broadcast to active WebSockets")
    persisted: bool = Field(..., description="Whether event was persisted to PostgreSQL")
    rule_id: Optional[uuid.UUID] = Field(None, description="Primary matched safety rule ID if any")
    matched_rules_count: int = Field(0, description="Number of safety rules matched by this event")
    should_notify: bool = Field(False, description="Whether any matched rule triggered notification")


class EventBatchIngestResponse(BaseModel):
    """API response after ingesting a batch or FrameResult."""
    total_received: int
    ingested_count: int
    duplicates_count: int
    events: List[EventIngestResponse]
