"""
tests/test_models.py
Verify integrity of SQLAlchemy models against Mohamed Salah's DDL schema.
"""
from app.models.base import Base
from app.models.enums import (
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
from app.models import (
    Alert,
    AlertDelivery,
    AuthToken,
    Camera,
    Department,
    Event,
    EvidenceFile,
    Factory,
    FactoryMembership,
    Incident,
    MonitoringZone,
    NotificationTarget,
    Permission,
    Role,
    RolePermission,
    SafetyRule,
    Sensor,
    SensorReading,
    UnobservedGap,
    User,
)


def test_models_metadata_has_all_tables():
    """Verify all 20 tables from Operix_Core_MVP_schema.sql are registered."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "factories",
        "users",
        "auth_tokens",
        "roles",
        "permissions",
        "role_permissions",
        "factory_memberships",
        "departments",
        "cameras",
        "sensors",
        "monitoring_zones",
        "safety_rules",
        "unobserved_gaps",
        "sensor_readings",
        "incidents",
        "events",
        "evidence_files",
        "alerts",
        "notification_targets",
        "alert_deliveries",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_models_primary_keys():
    """Verify primary keys are correctly defined on core models."""
    assert "id" in Base.metadata.tables["factories"].primary_key.columns
    assert "id" in Base.metadata.tables["users"].primary_key.columns
    assert "id" in Base.metadata.tables["cameras"].primary_key.columns
    assert "id" in Base.metadata.tables["events"].primary_key.columns
    assert "id" in Base.metadata.tables["incidents"].primary_key.columns
    assert "id" in Base.metadata.tables["safety_rules"].primary_key.columns

    # Composite primary keys
    fm_pk = [c.name for c in Base.metadata.tables["factory_memberships"].primary_key.columns]
    assert set(fm_pk) == {"factory_id", "user_id"}

    rp_pk = [c.name for c in Base.metadata.tables["role_permissions"].primary_key.columns]
    assert set(rp_pk) == {"role_id", "permission_id"}


def test_enums_completeness():
    """Verify enum members match DDL CREATE TYPE values."""
    assert EventType.PPE_VIOLATION.value == "ppe_violation"
    assert EventType.RESTRICTED_ZONE_INTRUSION.value == "restricted_zone_intrusion"
    assert EventType.FALL.value == "fall"
    assert SeverityLevel.CRITICAL.value == "critical"
    assert IncidentState.UNDER_REVIEW.value == "under_review"
    assert NotificationChannel.TELEGRAM.value == "telegram"
    assert FactoryStatus.ACTIVE.value == "active"


def test_composite_foreign_keys():
    """
    Verify multi-tenant composite foreign keys match Mohamed Salah's DDL schema:
    Every tenant child table FK must include factory_id to guarantee tenant boundary.
    """
    def get_fk_pairs(table_name: str):
        table = Base.metadata.tables[table_name]
        return [
            (
                tuple(fkc.column_keys),
                tuple(f.target_fullname for f in fkc.elements),
            )
            for fkc in table.foreign_key_constraints
        ]

    # cameras -> departments (factory_id, department_id)
    camera_fks = get_fk_pairs("cameras")
    assert (
        ("factory_id", "department_id"),
        ("departments.factory_id", "departments.id"),
    ) in camera_fks

    # sensors -> departments (factory_id, department_id)
    sensor_fks = get_fk_pairs("sensors")
    assert (
        ("factory_id", "department_id"),
        ("departments.factory_id", "departments.id"),
    ) in sensor_fks

    # monitoring_zones -> cameras and departments
    zone_fks = get_fk_pairs("monitoring_zones")
    assert (
        ("factory_id", "camera_id"),
        ("cameras.factory_id", "cameras.id"),
    ) in zone_fks
    assert (
        ("factory_id", "department_id"),
        ("departments.factory_id", "departments.id"),
    ) in zone_fks

    # safety_rules -> monitoring_zones, departments, sensors
    rule_fks = get_fk_pairs("safety_rules")
    assert (
        ("factory_id", "zone_id"),
        ("monitoring_zones.factory_id", "monitoring_zones.id"),
    ) in rule_fks
    assert (
        ("factory_id", "department_id"),
        ("departments.factory_id", "departments.id"),
    ) in rule_fks
    assert (
        ("factory_id", "sensor_id"),
        ("sensors.factory_id", "sensors.id"),
    ) in rule_fks

    # unobserved_gaps -> cameras
    gap_fks = get_fk_pairs("unobserved_gaps")
    assert (
        ("factory_id", "camera_id"),
        ("cameras.factory_id", "cameras.id"),
    ) in gap_fks

    # sensor_readings -> sensors
    reading_fks = get_fk_pairs("sensor_readings")
    assert (
        ("factory_id", "sensor_id"),
        ("sensors.factory_id", "sensors.id"),
    ) in reading_fks

    # events -> cameras, zones, rules, sensors, incidents
    event_fks = get_fk_pairs("events")
    assert (
        ("factory_id", "camera_id"),
        ("cameras.factory_id", "cameras.id"),
    ) in event_fks
    assert (
        ("factory_id", "zone_id"),
        ("monitoring_zones.factory_id", "monitoring_zones.id"),
    ) in event_fks
    assert (
        ("factory_id", "rule_id"),
        ("safety_rules.factory_id", "safety_rules.id"),
    ) in event_fks
    assert (
        ("factory_id", "sensor_id"),
        ("sensors.factory_id", "sensors.id"),
    ) in event_fks
    assert (
        ("factory_id", "incident_id"),
        ("incidents.factory_id", "incidents.id"),
    ) in event_fks

    # evidence_files -> events
    evidence_fks = get_fk_pairs("evidence_files")
    assert (
        ("factory_id", "event_id"),
        ("events.factory_id", "events.id"),
    ) in evidence_fks

    # alerts -> incidents
    alert_fks = get_fk_pairs("alerts")
    assert (
        ("factory_id", "incident_id"),
        ("incidents.factory_id", "incidents.id"),
    ) in alert_fks

    # alert_deliveries -> alerts and notification_targets
    delivery_fks = get_fk_pairs("alert_deliveries")
    assert (
        ("factory_id", "alert_id"),
        ("alerts.factory_id", "alerts.id"),
    ) in delivery_fks
    assert (
        ("factory_id", "target_id"),
        ("notification_targets.factory_id", "notification_targets.id"),
    ) in delivery_fks


def test_incident_reviewer_and_resolver_reference_factory_memberships():
    """
    Verify that incidents.reviewed_by and incidents.resolved_by reference
    factory_memberships(factory_id, user_id) rather than users(id) directly.
    """
    incidents_table = Base.metadata.tables["incidents"]
    incident_fks = [
        (
            tuple(fkc.column_keys),
            tuple(f.target_fullname for f in fkc.elements),
        )
        for fkc in incidents_table.foreign_key_constraints
    ]

    assert (
        ("factory_id", "reviewed_by"),
        ("factory_memberships.factory_id", "factory_memberships.user_id"),
    ) in incident_fks

    assert (
        ("factory_id", "resolved_by"),
        ("factory_memberships.factory_id", "factory_memberships.user_id"),
    ) in incident_fks


def test_check_constraints_and_indexes():
    """Verify critical DDL check constraints and indexes are present in SQLAlchemy metadata."""
    def get_constraint_names(table_name: str):
        table = Base.metadata.tables[table_name]
        return {c.name for c in table.constraints if c.name}

    def get_index_names(table_name: str):
        table = Base.metadata.tables[table_name]
        return {i.name for i in table.indexes if i.name}

    # Factories
    assert "ck_factories_retention_positive" in get_constraint_names("factories")

    # Users
    assert "ck_users_active_has_activation" in get_constraint_names("users")

    # Auth Tokens partial index
    assert "auth_tokens_user_idx" in get_index_names("auth_tokens")

    # Monitoring Zones
    assert "ck_monitoring_zone_polygon" in get_constraint_names("monitoring_zones")
    assert "monitoring_zones_camera_idx" in get_index_names("monitoring_zones")

    # Safety Rules
    assert "ck_rule_scope_exclusivity" in get_constraint_names("safety_rules")
    assert "ck_rule_min_confidence" in get_constraint_names("safety_rules")

    # Unobserved Gaps
    assert "ck_gap_ended_after_started" in get_constraint_names("unobserved_gaps")
    assert "unobserved_gaps_camera_idx" in get_index_names("unobserved_gaps")
    assert "unobserved_gaps_one_open" in get_index_names("unobserved_gaps")

    # Events
    assert "ck_event_single_source" in get_constraint_names("events")
    assert "ck_event_confidence_range" in get_constraint_names("events")
    assert "events_time_idx" in get_index_names("events")
    assert "events_camera_idx" in get_index_names("events")

    # Evidence Files
    assert "ck_evidence_size_positive" in get_constraint_names("evidence_files")
    assert "ck_evidence_clip_duration" in get_constraint_names("evidence_files")
    assert "ck_evidence_storage_key_pattern" in get_constraint_names("evidence_files")

    # Incidents
    assert "ck_incident_resolved_has_timestamp" in get_constraint_names("incidents")
    assert "incidents_open_idx" in get_index_names("incidents")


def test_partitioning_metadata():
    """Verify sensor_readings has PostgreSQL range partitioning configured."""
    table = Base.metadata.tables["sensor_readings"]
    assert table.dialect_options["postgresql"]["partition_by"] == "RANGE (recorded_at)"

