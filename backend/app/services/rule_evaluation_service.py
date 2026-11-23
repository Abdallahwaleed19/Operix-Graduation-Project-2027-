"""
app/services/rule_evaluation_service.py
Deterministic Safety Rule Evaluation Engine for real-time safety events.
Evaluates persisted events against enabled tenant rules without inventing side-effects.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.logging import logger
from ..models.enums import EventType, SeverityLevel
from ..models.incidents import Event
from ..models.operational import Camera, SafetyRule
from ..schemas.rules import RuleExecutionRecord, RuleViolation


@dataclass
class RuleMatchDetail:
    """Details of a single matched SafetyRule."""
    rule_id: uuid.UUID
    rule_name: str
    rule_version: int
    severity: SeverityLevel
    notify: bool
    scope_type: str  # 'global', 'zone', 'department', 'sensor'
    min_confidence: Optional[float]
    min_duration_s: Optional[int]
    threshold_value: Optional[Decimal]


@dataclass
class RuleEvaluationResult:
    """
    Standard typed result contract for Safety Rule evaluation.
    Can be consumed by EventService, WebSocket distribution,
    Workforce Analytics, RAG Assistant, and Reports.
    """
    event_id: uuid.UUID
    factory_id: uuid.UUID
    event_type: EventType
    evaluated_rule_ids: List[uuid.UUID] = field(default_factory=list)
    matched_rule_ids: List[uuid.UUID] = field(default_factory=list)
    unmatched_rule_ids: List[uuid.UUID] = field(default_factory=list)
    matches: List[RuleMatchDetail] = field(default_factory=list)
    execution_records: List[RuleExecutionRecord] = field(default_factory=list)
    violations: List[RuleViolation] = field(default_factory=list)
    evaluation_status: str = "evaluated"  # "evaluated", "no_rules_configured", "skipped"
    matched_highest_severity: Optional[SeverityLevel] = None
    event_context: Dict[str, Any] = field(default_factory=dict)


class RuleEvaluationService:
    """
    Deterministic rule evaluation engine.
    Follows shared session and transaction ownership:
      - Uses existing caller-owned SQLAlchemy Session.
      - Never commits, rolls back, or closes caller-owned sessions.
      - Operates strictly within tenant factory boundaries.
    """

    @classmethod
    def evaluate_event(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        event: Event,
    ) -> RuleEvaluationResult:
        """
        Evaluate an ingested and persisted Event against all active SafetyRules for the tenant.

        Scope hierarchy:
          - Sensor-scoped: matches if rule.sensor_id == event.sensor_id
          - Zone-scoped: matches if rule.zone_id == event.zone_id
          - Department-scoped: matches if rule.department_id == camera.department_id (via event.camera)
          - Global: matches if rule has no zone, department, or sensor specified.
        """
        result = RuleEvaluationResult(
            event_id=event.id,
            factory_id=factory_id,
            event_type=event.event_type,
            event_context={
                "confidence": event.confidence,
                "camera_id": str(event.camera_id) if event.camera_id else None,
                "zone_id": str(event.zone_id) if event.zone_id else None,
                "sensor_id": str(event.sensor_id) if event.sensor_id else None,
                "detected_at": event.detected_at.isoformat() if event.detected_at else None,
            },
        )

        # 1. Fetch enabled rules for this factory and target event_type
        stmt = (
            select(SafetyRule)
            .where(
                SafetyRule.factory_id == factory_id,
                SafetyRule.event_type == event.event_type,
                SafetyRule.is_enabled.is_(True),
            )
        )
        rules: List[SafetyRule] = list(db.execute(stmt).scalars().all())

        if not rules:
            result.evaluation_status = "no_rules_configured"
            return result

        result.evaluated_rule_ids = [r.id for r in rules]

        # 2. Resolve camera department if camera_id is present on event
        camera_department_id: Optional[uuid.UUID] = None
        if event.camera_id is not None:
            cam = db.execute(
                select(Camera.department_id).where(
                    Camera.id == event.camera_id,
                    Camera.factory_id == factory_id,
                )
            ).scalar_one_or_none()
            camera_department_id = cam

        # 3. Evaluate each rule deterministically
        now_utc = datetime.now(timezone.utc)
        for rule in rules:
            matched, scope_type, rejection_reason = cls._matches_rule(
                rule=rule,
                event=event,
                camera_department_id=camera_department_id,
            )

            # Build criteria dictionary
            threshold_summary = {
                "min_confidence": rule.min_confidence,
                "min_duration_s": rule.min_duration_s,
                "threshold_value": str(rule.threshold_value) if rule.threshold_value is not None else None,
            }

            # Create an in-memory execution record for audit/diagnostics
            exec_record = RuleExecutionRecord(
                event_id=event.id,
                factory_id=factory_id,
                rule_id=rule.id,
                rule_name=rule.name,
                rule_version=rule.version,
                evaluated_at=now_utc,
                is_matched=matched,
                rejection_reason=rejection_reason,
                scope_type=scope_type,
                severity=rule.severity,
                threshold_values=threshold_summary,
                execution_status="completed",
            )
            result.execution_records.append(exec_record)

            if matched:
                result.matched_rule_ids.append(rule.id)
                match_detail = RuleMatchDetail(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_version=rule.version,
                    severity=rule.severity,
                    notify=rule.notify,
                    scope_type=scope_type,
                    min_confidence=rule.min_confidence,
                    min_duration_s=rule.min_duration_s,
                    threshold_value=rule.threshold_value,
                )
                result.matches.append(match_detail)

                # Instantiate typed RuleViolation
                violation = RuleViolation(
                    event_id=event.id,
                    factory_id=factory_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_version=rule.version,
                    incident_id=event.incident_id,
                    event_type=event.event_type,
                    severity=rule.severity,
                    violation_status="detected",
                    detected_at=event.detected_at,
                    scope_type=scope_type,
                    camera_id=event.camera_id,
                    zone_id=event.zone_id,
                    sensor_id=event.sensor_id,
                    confidence=event.confidence,
                    details=event.details if isinstance(event.details, dict) else {},
                )
                result.violations.append(violation)

                # Track highest severity among matches
                result.matched_highest_severity = cls._select_higher_severity(
                    result.matched_highest_severity,
                    rule.severity,
                )
            else:
                result.unmatched_rule_ids.append(rule.id)

        # 4. If at least one rule matched and the event has no rule_id linked, link the primary (highest severity) rule
        if result.matches and event.rule_id is None:
            primary_match = result.matches[0]
            # Prefer match with highest severity
            for m in result.matches:
                if m.severity == result.matched_highest_severity:
                    primary_match = m
                    break
            event.rule_id = primary_match.rule_id
            db.flush()

        logger.info(
            f"Evaluated event {event.id} [{event.event_type.value}]: "
            f"{len(result.matched_rule_ids)}/{len(rules)} rules matched."
        )
        return result

    @classmethod
    def _matches_rule(
        cls,
        rule: SafetyRule,
        event: Event,
        camera_department_id: Optional[uuid.UUID],
    ) -> tuple[bool, str, Optional[str]]:
        """
        Check if an event satisfies all criteria of a safety rule:
        1. Scope match
        2. Confidence threshold
        3. Duration threshold (if duration verifiable in event details)
        4. Sensor threshold value (if sensor metric verifiable in event details)

        Returns:
            (is_matched, scope_type, rejection_reason)
        """
        # Scope matching
        scope_matched = False
        scope_type = "global"

        if rule.sensor_id is not None:
            scope_type = "sensor"
            if event.sensor_id is not None and event.sensor_id == rule.sensor_id:
                scope_matched = True
        elif rule.zone_id is not None:
            scope_type = "zone"
            if event.zone_id is not None and event.zone_id == rule.zone_id:
                scope_matched = True
        elif rule.department_id is not None:
            scope_type = "department"
            if camera_department_id is not None and camera_department_id == rule.department_id:
                scope_matched = True
        else:
            # Global rule (no specific sensor, zone, or department scope)
            scope_type = "global"
            scope_matched = True

        if not scope_matched:
            return False, scope_type, "scope_mismatch"

        # Confidence evaluation
        if rule.min_confidence is not None:
            if event.confidence is None or event.confidence < rule.min_confidence:
                return False, scope_type, "confidence_below_threshold"

        # Duration evaluation:
        # Check if event has a reliable duration specified in its details
        if rule.min_duration_s is not None and rule.min_duration_s > 0:
            duration_s = cls._extract_duration_seconds(event)
            if duration_s is None or duration_s < rule.min_duration_s:
                return False, scope_type, "duration_insufficient"

        # Sensor threshold evaluation:
        # Check if event provides a measured value (e.g. temperature, gas level)
        if rule.threshold_value is not None:
            measured_val = cls._extract_threshold_metric(event)
            if measured_val is None or measured_val < rule.threshold_value:
                return False, scope_type, "threshold_metric_unmet"

        return True, scope_type, None

    @staticmethod
    def _extract_duration_seconds(event: Event) -> Optional[float]:
        """
        Extract reliably computed duration in seconds from event details if present.
        Looks for 'duration_s', 'duration_seconds', or 'duration'.
        """
        if not event.details or not isinstance(event.details, dict):
            return None

        for key in ("duration_s", "duration_seconds", "duration"):
            val = event.details.get(key)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _extract_threshold_metric(event: Event) -> Optional[Decimal]:
        """
        Extract numerical measured metric from event details if present.
        Looks for 'reading_value', 'value', 'temperature', 'level', or 'metric_value'.
        """
        if not event.details or not isinstance(event.details, dict):
            return None

        for key in ("reading_value", "value", "temperature", "metric_value", "level"):
            val = event.details.get(key)
            if val is not None:
                try:
                    return Decimal(str(val))
                except Exception:
                    pass
        return None

    @staticmethod
    def _select_higher_severity(
        current: Optional[SeverityLevel],
        candidate: SeverityLevel,
    ) -> SeverityLevel:
        """Severity order: low < medium < high < critical."""
        severity_rank = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        if current is None:
            return candidate
        curr_rank = severity_rank.get(current, 0)
        cand_rank = severity_rank.get(candidate, 0)
        return candidate if cand_rank > curr_rank else current
