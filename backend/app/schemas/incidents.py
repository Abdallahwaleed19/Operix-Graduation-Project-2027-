"""
app/schemas/incidents.py
Pydantic schemas for Incidents Management API (/api/v1/incidents/*).
"""
from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import EventType, IncidentState, SeverityLevel


class IncidentCreate(BaseModel):
    incident_type: EventType
    severity: SeverityLevel = SeverityLevel.MEDIUM


class IncidentUpdate(BaseModel):
    severity: Optional[SeverityLevel] = None
    resolution_note: Optional[str] = Field(default=None, max_length=2000)


class IncidentResolveRequest(BaseModel):
    resolution_note: Optional[str] = Field(default=None, max_length=2000)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    factory_id: uuid.UUID
    incident_type: EventType
    severity: SeverityLevel
    state: IncidentState
    opened_at: datetime
    last_event_at: datetime
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    resolved_by: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    updated_at: datetime


class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    total: int
