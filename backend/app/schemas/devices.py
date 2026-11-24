"""
app/schemas/devices.py
Pydantic schemas for Cameras and Sensors Management API (/api/v1/devices/*).
"""
from datetime import datetime
import re
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.enums import CameraType, SensorType, SourceStatus

_URL_CREDENTIALS_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)([^/\s]+)@")


class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    camera_type: CameraType = CameraType.CCTV
    department_id: Optional[uuid.UUID] = None
    location_label: Optional[str] = Field(default=None, max_length=200)
    stream_url_ref: str = Field(..., min_length=1, max_length=500)
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    camera_type: Optional[CameraType] = None
    department_id: Optional[uuid.UUID] = None
    location_label: Optional[str] = Field(default=None, max_length=200)
    stream_url_ref: Optional[str] = Field(default=None, min_length=1, max_length=500)
    status: Optional[SourceStatus] = None
    is_active: Optional[bool] = None


class CameraResponse(BaseModel):
    """
    Public camera metadata.
    `stream_url_ref` is a secret-store reference or RTSP stream reference;
    any embedded `user:pass@` URL credentials are masked before serialization.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    factory_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    name: str
    camera_type: CameraType
    location_label: Optional[str] = None
    stream_url_ref: str
    status: SourceStatus
    status_since: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("stream_url_ref", mode="before")
    @classmethod
    def _mask_embedded_credentials(cls, value: str) -> str:
        if isinstance(value, str):
            return _URL_CREDENTIALS_RE.sub(r"\1***:***@", value)
        return value


class CameraListResponse(BaseModel):
    items: List[CameraResponse]
    total: int


class SensorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sensor_type: SensorType = SensorType.TEMPERATURE
    unit: str = Field(default="C", min_length=1, max_length=8)
    department_id: Optional[uuid.UUID] = None
    location_label: Optional[str] = Field(default=None, max_length=200)
    sampling_interval_s: int = Field(default=60, ge=1)
    is_active: bool = True


class SensorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    sensor_type: Optional[SensorType] = None
    unit: Optional[str] = Field(default=None, min_length=1, max_length=8)
    department_id: Optional[uuid.UUID] = None
    location_label: Optional[str] = Field(default=None, max_length=200)
    sampling_interval_s: Optional[int] = Field(default=None, ge=1)
    status: Optional[SourceStatus] = None
    is_active: Optional[bool] = None


class SensorResponse(BaseModel):
    """Public sensor metadata (explicitly excludes device_key_hash)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    factory_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    name: str
    sensor_type: SensorType
    unit: str
    location_label: Optional[str] = None
    sampling_interval_s: int
    status: SourceStatus
    status_since: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SensorListResponse(BaseModel):
    items: List[SensorResponse]
    total: int


class SensorReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sensor_id: uuid.UUID
    recorded_at: datetime
    factory_id: uuid.UUID
    value: float
    ingested_at: datetime


class SensorReadingListResponse(BaseModel):
    items: List[SensorReadingResponse]
    total: int
