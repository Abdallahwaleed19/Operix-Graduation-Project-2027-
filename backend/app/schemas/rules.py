"""
app/schemas/rules.py
Pydantic schemas for Safety Rule configuration, validation, and serialization.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field, model_validator

from ..models.enums import EventType, SeverityLevel


class SafetyRuleBase(BaseModel):
    """Base fields for safety rules."""
    name: str = Field(..., min_length=1, max_length=120, description="Descriptive rule title")
    event_type: EventType = Field(..., description="Target event type to monitor")
    severity: SeverityLevel = Field(..., description="Severity level assigned when rule triggers")
    zone_id: Optional[uuid.UUID] = Field(default=None, description="Scope to a specific monitoring zone")
    department_id: Optional[uuid.UUID] = Field(default=None, description="Scope to a specific department")
    sensor_id: Optional[uuid.UUID] = Field(default=None, description="Scope to a specific sensor")
    min_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Minimum detection confidence required"
    )
    min_duration_s: Optional[int] = Field(
        default=None, ge=0, description="Minimum event duration in seconds before triggering"
    )
    threshold_value: Optional[Decimal] = Field(
        default=None, description="Numeric threshold for sensor or metric evaluation"
    )
    notify: bool = Field(default=True, description="Whether to dispatch alerts when triggered")
    is_enabled: bool = Field(default=True, description="Whether rule is currently evaluated")


class SafetyRuleCreate(SafetyRuleBase):
    """Payload for creating a new Safety Rule."""

    @model_validator(mode="after")
    def validate_scope_exclusivity(self) -> "SafetyRuleCreate":
        scopes = [self.zone_id, self.department_id, self.sensor_id]
        non_null_count = sum(1 for s in scopes if s is not None)
        if non_null_count > 1:
            raise ValueError(
                "Scope exclusivity violation: At most one of zone_id, department_id, or sensor_id may be specified."
            )
        return self


class SafetyRuleUpdate(BaseModel):
    """Payload for updating an existing Safety Rule (partial or full)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    event_type: Optional[EventType] = None
    severity: Optional[SeverityLevel] = None
    zone_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    sensor_id: Optional[uuid.UUID] = None
    clear_scope: Optional[bool] = Field(
        default=False,
        description="If true and all scope fields are None, resets rule scope to factory-global",
    )
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_duration_s: Optional[int] = Field(default=None, ge=0)
    threshold_value: Optional[Decimal] = None
    notify: Optional[bool] = None
    is_enabled: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update_scope_exclusivity(self) -> "SafetyRuleUpdate":
        scopes = [self.zone_id, self.department_id, self.sensor_id]
        non_null_count = sum(1 for s in scopes if s is not None)
        if non_null_count > 1:
            raise ValueError(
                "Scope exclusivity violation: At most one of zone_id, department_id, or sensor_id may be specified."
            )
        return self


class SafetyRuleStatusUpdate(BaseModel):
    """Payload for toggling the active state of a Safety Rule."""
    is_enabled: bool = Field(..., description="Desired operational state of the rule")


class SafetyRuleResponse(BaseModel):
    """Standard serialized representation of a Safety Rule."""
    id: uuid.UUID
    factory_id: uuid.UUID
    name: str
    event_type: EventType
    severity: SeverityLevel
    zone_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    sensor_id: Optional[uuid.UUID] = None
    min_confidence: Optional[float] = None
    min_duration_s: Optional[int] = None
    threshold_value: Optional[Decimal] = None
    notify: bool
    is_enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SafetyRuleListResponse(BaseModel):
    """List response envelope for safety rules."""
    items: List[SafetyRuleResponse]
    total: int


# =============================================================================
# Phase 3.4 Contracts: Rule Execution Record & Rule Violation
# =============================================================================

class RuleExecutionRecord(BaseModel):
    """
    Contract representing the evaluation outcome of a specific Safety Rule against an Event.
    Can be serialized for in-memory dispatch, logging, audit reporting, or future persistence.
    """
    event_id: uuid.UUID = Field(..., description="Unique event identifier evaluated")
    factory_id: uuid.UUID = Field(..., description="Tenant factory identifier")
    rule_id: uuid.UUID = Field(..., description="Evaluated safety rule identifier")
    rule_name: str = Field(..., description="Descriptive name of the evaluated rule")
    rule_version: int = Field(default=1, description="Version of the rule definition at evaluation time")
    evaluated_at: datetime = Field(..., description="UTC timestamp of evaluation execution")
    is_matched: bool = Field(..., description="Whether the rule criteria matched the event")
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Reason if rule did not match (e.g. 'scope_mismatch', 'confidence_below_threshold', 'duration_insufficient')",
    )
    scope_type: str = Field(..., description="'global', 'zone', 'department', or 'sensor'")
    severity: SeverityLevel = Field(..., description="Severity level configured on the rule")
    threshold_values: Optional[dict] = Field(
        default=None,
        description="Summary of criteria evaluated (min_confidence, min_duration_s, threshold_value)",
    )
    execution_status: str = Field(default="completed", description="Execution lifecycle state: 'completed', 'skipped', 'failed'")


class RuleViolation(BaseModel):
    """
    Contract representing a confirmed safety violation triggered by a matched Safety Rule.
    Readily consumable by Workforce Analytics, RAG Assistant, and Reports Generation.
    """
    violation_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique violation event reference identifier",
    )
    event_id: uuid.UUID = Field(..., description="Underlying detection event ID")
    factory_id: uuid.UUID = Field(..., description="Tenant factory scope")
    rule_id: uuid.UUID = Field(..., description="Triggered safety rule ID")
    rule_name: str = Field(..., description="Triggered safety rule name")
    rule_version: int = Field(default=1, description="Rule version at time of violation")
    incident_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Associated Incident ID if correlated or grouped",
    )
    event_type: EventType = Field(..., description="Classification of the safety event")
    severity: SeverityLevel = Field(..., description="Assigned severity of the violation")
    violation_status: str = Field(
        default="detected",
        description="State of violation: 'detected', 'correlated', 'alerted'",
    )
    detected_at: datetime = Field(..., description="UTC timestamp when violation was detected")
    scope_type: str = Field(..., description="'global', 'zone', 'department', or 'sensor'")
    camera_id: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None
    sensor_id: Optional[uuid.UUID] = None
    confidence: Optional[float] = None
    details: Optional[dict] = Field(default_factory=dict, description="Contextual event metadata")

