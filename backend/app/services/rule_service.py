"""
app/services/rule_service.py
Service layer handling Safety Rule persistence, updates, scope validation, and factory isolation.
"""
from typing import List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.errors import OperixException, ResourceNotFoundException, TenantAccessDeniedException
from ..core.logging import logger
from ..models.incidents import Event
from ..models.operational import Camera, Department, MonitoringZone, SafetyRule, Sensor
from ..schemas.rules import SafetyRuleCreate, SafetyRuleStatusUpdate, SafetyRuleUpdate


class RuleService:
    """
    Encapsulates all Safety Rule business operations.
    Follows shared session contract:
      - Accepts caller-owned Session.
      - NEVER calls commit(), rollback(), or close() on caller-owned Session.
      - Strictly isolates queries by factory_id.
    """

    @staticmethod
    def _validate_scope_factory(
        db: Session,
        factory_id: uuid.UUID,
        zone_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        sensor_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Verify that referenced scope entities belong to the specified tenant factory.
        Raises ResourceNotFoundException if an entity does not exist or belongs to another tenant.
        """
        if zone_id is not None:
            zone = db.execute(
                select(MonitoringZone).where(
                    MonitoringZone.id == zone_id,
                    MonitoringZone.factory_id == factory_id,
                )
            ).scalar_one_or_none()
            if not zone:
                raise ResourceNotFoundException(
                    "MonitoringZone",
                    f"{zone_id} (or zone does not belong to authorized factory)",
                )

        if department_id is not None:
            dept = db.execute(
                select(Department).where(
                    Department.id == department_id,
                    Department.factory_id == factory_id,
                )
            ).scalar_one_or_none()
            if not dept:
                raise ResourceNotFoundException(
                    "Department",
                    f"{department_id} (or department does not belong to authorized factory)",
                )

        if sensor_id is not None:
            sensor = db.execute(
                select(Sensor).where(
                    Sensor.id == sensor_id,
                    Sensor.factory_id == factory_id,
                )
            ).scalar_one_or_none()
            if not sensor:
                raise ResourceNotFoundException(
                    "Sensor",
                    f"{sensor_id} (or sensor does not belong to authorized factory)",
                )

    @classmethod
    def create_rule(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        rule_in: SafetyRuleCreate,
    ) -> SafetyRule:
        """Create a new safety rule bound to tenant factory."""
        # 1. Validate foreign reference scopes belong to the same factory
        cls._validate_scope_factory(
            db=db,
            factory_id=factory_id,
            zone_id=rule_in.zone_id,
            department_id=rule_in.department_id,
            sensor_id=rule_in.sensor_id,
        )

        # 2. Instantiate SafetyRule model
        rule = SafetyRule(
            factory_id=factory_id,
            name=rule_in.name,
            event_type=rule_in.event_type,
            severity=rule_in.severity,
            zone_id=rule_in.zone_id,
            department_id=rule_in.department_id,
            sensor_id=rule_in.sensor_id,
            min_confidence=rule_in.min_confidence,
            min_duration_s=rule_in.min_duration_s,
            threshold_value=rule_in.threshold_value,
            notify=rule_in.notify,
            is_enabled=rule_in.is_enabled,
            version=1,
        )
        db.add(rule)
        db.flush()
        logger.info(f"Created SafetyRule {rule.id} ('{rule.name}') for factory {factory_id}")
        return rule

    @classmethod
    def get_rule(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> SafetyRule:
        """Retrieve a specific safety rule with factory isolation."""
        rule = db.execute(
            select(SafetyRule).where(
                SafetyRule.id == rule_id,
                SafetyRule.factory_id == factory_id,
            )
        ).scalar_one_or_none()

        if not rule:
            raise ResourceNotFoundException("SafetyRule", rule_id)
        return rule

    @classmethod
    def list_rules(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        is_enabled: Optional[bool] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[SafetyRule], int]:
        """List safety rules for tenant with filtering and total count."""
        query = select(SafetyRule).where(SafetyRule.factory_id == factory_id)

        if is_enabled is not None:
            query = query.where(SafetyRule.is_enabled == is_enabled)
        if event_type is not None:
            query = query.where(SafetyRule.event_type == event_type)

        count_query = select(func.count()).select_from(query.subquery())
        total = db.execute(count_query).scalar_one()

        query = query.order_by(SafetyRule.created_at.desc()).limit(limit).offset(offset)
        items = list(db.execute(query).scalars().all())
        return items, total

    @classmethod
    def update_rule(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        rule_id: uuid.UUID,
        rule_in: SafetyRuleUpdate,
    ) -> SafetyRule:
        """Update safety rule parameters and increment version."""
        rule = cls.get_rule(db=db, factory_id=factory_id, rule_id=rule_id)

        update_data = rule_in.model_dump(exclude_unset=True)

        # Check scope exclusivity against existing fields if partially updated
        new_zone = update_data.get("zone_id", rule.zone_id)
        new_dept = update_data.get("department_id", rule.department_id)
        new_sensor = update_data.get("sensor_id", rule.sensor_id)

        if update_data.get("clear_scope", False):
            # Explicitly reset all scope targets to factory-global
            new_zone = None
            new_dept = None
            new_sensor = None
            rule.zone_id = None
            rule.department_id = None
            rule.sensor_id = None

        scopes = [new_zone, new_dept, new_sensor]
        if sum(1 for s in scopes if s is not None) > 1:
            raise OperixException(
                message="Scope exclusivity violation: At most one of zone_id, department_id, or sensor_id may be specified.",
                status_code=422,
                error_code="SCOPE_EXCLUSIVITY_VIOLATION",
            )

        # Validate that any newly specified scope target belongs to this tenant factory
        cls._validate_scope_factory(
            db=db,
            factory_id=factory_id,
            zone_id=new_zone,
            department_id=new_dept,
            sensor_id=new_sensor,
        )

        has_changes = False
        for field, value in update_data.items():
            if field in ("clear_scope",):
                continue
            if hasattr(rule, field) and getattr(rule, field) != value:
                setattr(rule, field, value)
                has_changes = True

        if has_changes:
            rule.version += 1
            db.flush()
            logger.info(f"Updated SafetyRule {rule.id} to version {rule.version}")

        return rule

    @classmethod
    def update_rule_status(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        rule_id: uuid.UUID,
        status_in: SafetyRuleStatusUpdate,
    ) -> SafetyRule:
        """Toggle is_enabled state on a rule."""
        rule = cls.get_rule(db=db, factory_id=factory_id, rule_id=rule_id)
        if rule.is_enabled != status_in.is_enabled:
            rule.is_enabled = status_in.is_enabled
            rule.version += 1
            db.flush()
            logger.info(f"Toggled SafetyRule {rule.id} status to is_enabled={rule.is_enabled}")
        return rule

    @classmethod
    def delete_rule(
        cls,
        db: Session,
        factory_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> None:
        """
        Delete a safety rule safely.
        Foreign key constraint check:
          events table has `fk_event_rule` with `ON DELETE SET NULL`.
          Therefore physical deletion is safe under PostgreSQL and database relationships.
        """
        rule = cls.get_rule(db=db, factory_id=factory_id, rule_id=rule_id)
        db.delete(rule)
        db.flush()
        logger.info(f"Deleted SafetyRule {rule_id} for factory {factory_id}")
