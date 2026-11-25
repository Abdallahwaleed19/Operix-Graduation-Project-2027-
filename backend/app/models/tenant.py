"""
app/models/tenant.py
Tenant, user identity, authentication, and RBAC models.
Directly maps to Operix_Core_MVP_schema.sql (lines 38-106).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import FactoryStatus, TokenPurpose, UserStatus


class Factory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "factories"
    __table_args__ = (
        CheckConstraint("evidence_retention_days > 0", name="ck_factories_retention_positive"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    status: Mapped[FactoryStatus] = mapped_column(
        Enum(FactoryStatus, name="factory_status", native_enum=True,
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=FactoryStatus.ACTIVE,
    )
    timezone: Mapped[str] = mapped_column(String(40), nullable=False, default="UTC")
    evidence_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Relationships
    memberships = relationship("FactoryMembership", back_populates="factory", cascade="all, delete-orphan")


class User(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status <> 'active' OR activated_at IS NOT NULL", name="ck_users_active_has_activation"),
    )

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=True,
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=UserStatus.INVITED,
    )
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")
    memberships = relationship("FactoryMembership", back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "auth_tokens"
    __table_args__ = (
        Index(
            "auth_tokens_user_idx",
            "user_id",
            "purpose",
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    purpose: Mapped[TokenPurpose] = mapped_column(
        Enum(TokenPurpose, name="token_purpose", native_enum=True,
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="tokens")


class Role(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)


class Permission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class FactoryMembership(Base):
    __tablename__ = "factory_memberships"
    __table_args__ = (
        Index("factory_memberships_user_idx", "user_id"),
    )

    factory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    factory = relationship("Factory", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    role = relationship("Role")
