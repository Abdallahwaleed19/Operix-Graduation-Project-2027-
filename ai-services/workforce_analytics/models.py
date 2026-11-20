"""
workforce_analytics/models.py
SQLAlchemy ORM model stubs — for reference only.

NOTE: The analytics module uses raw SQL via text() in repositories.py and does NOT
depend on these ORM models at runtime. They are provided here as:
  1. Documentation of the relevant Operix tables and columns.
  2. A starting point if a future developer wants to switch to ORM-style queries.

Do NOT use these models to auto-create or modify the database schema.
The schema is owned by the main Operix DDL (DataBase/ddl/).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Core tenant / access tables
# ---------------------------------------------------------------------------

class Factory(Base):
    __tablename__ = "factories"

    id                   = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                 = Column(String, nullable=False)
    slug                 = Column(String, nullable=False, unique=True)
    timezone             = Column(String)
    evidence_retention_days = Column(Integer)
    created_at           = Column(DateTime(timezone=True))
    updated_at           = Column(DateTime(timezone=True))


class Role(Base):
    __tablename__ = "roles"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"))
    code       = Column(String, nullable=False)
    name       = Column(String, nullable=False)


class User(Base):
    __tablename__ = "users"

    id               = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id       = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"), nullable=False)
    email            = Column(String, nullable=False)
    full_name        = Column(String)
    status           = Column(String)   # 'active' | 'invited' | 'disabled'
    is_platform_admin = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True))


class FactoryMembership(Base):
    __tablename__ = "factory_memberships"
    __table_args__ = (UniqueConstraint("factory_id", "user_id"),)

    factory_id = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"), primary_key=True)
    user_id    = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"),    primary_key=True)
    role_id    = Column(PG_UUID(as_uuid=True), ForeignKey("roles.id"),    nullable=False)
    is_active  = Column(Boolean, default=True)
    joined_at  = Column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Operational tables (cameras, zones, incidents)
# ---------------------------------------------------------------------------

class Department(Base):
    __tablename__ = "departments"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"), nullable=False)
    name       = Column(String, nullable=False)


class Camera(Base):
    __tablename__ = "cameras"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id    = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"), nullable=False)
    department_id = Column(PG_UUID(as_uuid=True), ForeignKey("departments.id"))
    name          = Column(String, nullable=False)
    camera_type   = Column(String)
    status        = Column(String)   # 'active' | 'inactive' | 'maintenance'
    is_active     = Column(Boolean,  default=True)
    stream_url_ref = Column(String)


class UnobservedGap(Base):
    """Camera downtime windows."""
    __tablename__ = "unobserved_gaps"

    id         = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"), nullable=False)
    camera_id  = Column(PG_UUID(as_uuid=True), ForeignKey("cameras.id"),   nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at   = Column(DateTime(timezone=True))   # NULL = still ongoing
    reason     = Column(Text)


class Incident(Base):
    __tablename__ = "incidents"

    id            = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    factory_id    = Column(PG_UUID(as_uuid=True), ForeignKey("factories.id"), nullable=False)
    incident_type = Column(String, nullable=False)
    severity      = Column(String, nullable=False)  # 'low'|'medium'|'high'|'critical'
    state         = Column(String, nullable=False)  # 'detected'|...|'resolved'
    opened_at     = Column(DateTime(timezone=True), nullable=False)
    reviewed_at   = Column(DateTime(timezone=True))
    reviewed_by   = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_at   = Column(DateTime(timezone=True))
    resolved_by   = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    # NOTE: schema constraint — resolved incidents MUST have resolved_at:
    #   CHECK (state <> 'resolved' OR resolved_at IS NOT NULL)


# ---------------------------------------------------------------------------
# SCHEMA GAPS (documented, not modelled)
# ---------------------------------------------------------------------------
#
# The following analytics capabilities are NOT available because the
# corresponding tables do not exist in the Operix schema:
#
#   ❌ Attendance / clock-in / clock-out table  → no shifts/timesheets
#   ❌ Working hours / overtime                 → no work_logs table
#   ❌ Direct user↔department link              → only cameras have department_id
#   ❌ Tasks / work assignments                 → no task table
#   ❌ Direct performance scores               → no performance_reviews table
#
# Proxy metrics used instead:
#   ✅ Attendance proxy  = incident review/resolve activity
#   ✅ Productivity proxy = count of incidents reviewed + resolved per worker
#
# ---------------------------------------------------------------------------
