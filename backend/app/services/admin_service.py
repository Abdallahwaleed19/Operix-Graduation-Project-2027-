"""
app/services/admin_service.py
Business logic for S-4 Users, Roles/Permissions, and Factory Settings.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.errors import OperixException, ResourceNotFoundException
from ..core.security import AuthorizationException, generate_refresh_token, hash_password, hash_refresh_token
from .email_service import EmailService
from ..models.enums import TokenPurpose, UserStatus
from ..models.tenant import (
    AuthToken,
    Factory,
    FactoryMembership,
    Permission,
    Role,
    RolePermission,
    User,
)
from ..schemas.admin import (
    FactorySettingsUpdate,
    FactoryUserResponse,
    PermissionResponse,
    RoleResponse,
    UserInviteRequest,
    UserUpdateRequest,
)


_ROLE_RANK = {
    "viewer": 10,
    "worker": 20,
    "operator": 20,
    "safety_supervisor": 30,
    "factory_manager": 40,
    "factory_admin": 50,
    "platform_admin": 100,
}


class AdminService:
    """Caller owns DB session commit/rollback."""

    @staticmethod
    def _assert_can_assign_role(actor_role: Optional[str], target_role_code: str) -> None:
        """
        Enforce role-assignment hierarchy at the service layer:
        - platform_admin can never be assigned via tenant-scoped APIs.
        - factory_manager can only assign roles strictly below factory_manager.
        - factory_admin can assign factory_admin and lower factory roles.
        """
        actor = (actor_role or "").strip().lower()
        target = target_role_code.strip().lower()

        if target == "platform_admin":
            raise AuthorizationException(
                "Platform-level roles cannot be assigned through tenant management.",
                error_code="INSUFFICIENT_PERMISSIONS",
            )

        actor_rank = _ROLE_RANK.get(actor, 0)
        target_rank = _ROLE_RANK.get(target)
        if target_rank is None:
            raise AuthorizationException(
                f"Role '{target_role_code}' is not assignable.",
                error_code="INSUFFICIENT_PERMISSIONS",
            )

        if actor == "factory_manager":
            if target_rank >= _ROLE_RANK["factory_manager"]:
                raise AuthorizationException(
                    "Factory managers cannot assign roles equal to or higher than factory_manager.",
                    error_code="INSUFFICIENT_PERMISSIONS",
                )
        elif actor in ("factory_admin", "platform_admin"):
            if actor_rank < target_rank:
                raise AuthorizationException(
                    "Insufficient privileges to assign the requested role.",
                    error_code="INSUFFICIENT_PERMISSIONS",
                )
        else:
            raise AuthorizationException(
                "Insufficient permissions to assign roles.",
                error_code="INSUFFICIENT_PERMISSIONS",
            )

    @staticmethod
    def _to_user_response(user: User, membership: FactoryMembership, role: Role) -> FactoryUserResponse:
        return FactoryUserResponse(
            user_id=user.id,
            factory_id=membership.factory_id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            role_id=role.id,
            role_code=role.code,
            role_name=role.name,
            membership_active=membership.is_active,
            activated_at=user.activated_at,
            created_at=user.created_at,
        )

    @staticmethod
    def list_factory_users(
        db: Session,
        factory_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[FactoryUserResponse], int]:
        base_stmt = (
            select(User, FactoryMembership, Role)
            .join(FactoryMembership, FactoryMembership.user_id == User.id)
            .join(Role, Role.id == FactoryMembership.role_id)
            .where(FactoryMembership.factory_id == factory_id)
        )
        total = db.execute(
            select(func.count())
            .select_from(FactoryMembership)
            .where(FactoryMembership.factory_id == factory_id)
        ).scalar_one()

        rows = db.execute(
            base_stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return [AdminService._to_user_response(r[0], r[1], r[2]) for r in rows], int(total)

    @staticmethod
    def get_factory_user(
        db: Session,
        factory_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> FactoryUserResponse:
        row = db.execute(
            select(User, FactoryMembership, Role)
            .join(FactoryMembership, FactoryMembership.user_id == User.id)
            .join(Role, Role.id == FactoryMembership.role_id)
            .where(
                FactoryMembership.factory_id == factory_id,
                User.id == target_user_id,
            )
        ).first()
        if row is None:
            raise ResourceNotFoundException("User", target_user_id)
        return AdminService._to_user_response(row[0], row[1], row[2])

    @staticmethod
    def invite_user(
        db: Session,
        factory_id: uuid.UUID,
        invite_in: UserInviteRequest,
        *,
        actor_role: str,
    ) -> FactoryUserResponse:
        AdminService._assert_can_assign_role(actor_role, invite_in.role_code)
        normalized_email = invite_in.email.strip().lower()
        role = db.execute(select(Role).where(Role.code == invite_in.role_code.strip())).scalar_one_or_none()
        if role is None:
            raise ResourceNotFoundException("Role", invite_in.role_code)

        existing_user = db.execute(
            select(User).where(func.lower(User.email) == normalized_email)
        ).scalar_one_or_none()
        if existing_user is not None:
            existing_membership = db.execute(
                select(FactoryMembership).where(
                    FactoryMembership.factory_id == factory_id,
                    FactoryMembership.user_id == existing_user.id,
                )
            ).scalar_one_or_none()
            if existing_membership is not None:
                raise OperixException(
                    message=f"User '{normalized_email}' is already a member of this factory.",
                    status_code=409,
                    error_code="USER_ALREADY_EXISTS",
                )
            user = existing_user
        else:
            user = User(
                email=normalized_email,
                password_hash=hash_password(generate_refresh_token()),
                full_name=invite_in.full_name.strip(),
                status=UserStatus.INVITED,
            )
            db.add(user)
            db.flush()
            db.add(
                AuthToken(
                    user_id=user.id,
                    purpose=TokenPurpose.ACTIVATION,
                    token_hash=hash_refresh_token(generate_refresh_token()),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
            )

        membership = FactoryMembership(
            factory_id=factory_id,
            user_id=user.id,
            role_id=role.id,
            is_active=True,
        )
        db.add(membership)
        db.flush()
        db.refresh(user)
        db.refresh(membership)

        factory = db.get(Factory, factory_id)
        EmailService.send_invite_email(
            to_email=user.email,
            full_name=user.full_name,
            role_name=role.name,
            factory_name=factory.name if factory else "Operix Factory",
        )
        return AdminService._to_user_response(user, membership, role)

    @staticmethod
    def update_factory_user(
        db: Session,
        factory_id: uuid.UUID,
        target_user_id: uuid.UUID,
        update_in: UserUpdateRequest,
        *,
        actor_role: Optional[str] = None,
    ) -> FactoryUserResponse:
        if update_in.role_code is not None:
            AdminService._assert_can_assign_role(actor_role, update_in.role_code)
        row = db.execute(
            select(User, FactoryMembership, Role)
            .join(FactoryMembership, FactoryMembership.user_id == User.id)
            .join(Role, Role.id == FactoryMembership.role_id)
            .where(
                FactoryMembership.factory_id == factory_id,
                User.id == target_user_id,
            )
        ).first()
        if row is None:
            raise ResourceNotFoundException("User", target_user_id)

        user, membership, role = row[0], row[1], row[2]
        was_invited = user.status == UserStatus.INVITED
        if update_in.full_name is not None:
            user.full_name = update_in.full_name.strip()
        if update_in.status is not None:
            if update_in.status == UserStatus.ACTIVE and user.activated_at is None:
                user.activated_at = datetime.now(timezone.utc)
            user.status = update_in.status
        if update_in.membership_active is not None:
            membership.is_active = update_in.membership_active
        if update_in.role_code is not None:
            new_role = db.execute(
                select(Role).where(Role.code == update_in.role_code.strip())
            ).scalar_one_or_none()
            if new_role is None:
                raise ResourceNotFoundException("Role", update_in.role_code)
            membership.role_id = new_role.id
            role = new_role

        db.flush()
        db.refresh(user)
        db.refresh(membership)

        if was_invited and user.status == UserStatus.ACTIVE and membership.is_active:
            factory = db.get(Factory, factory_id)
            EmailService.send_account_approved_email(
                to_email=user.email,
                full_name=user.full_name,
                role_name=role.name,
                factory_name=factory.name if factory else "Operix Factory",
            )

        return AdminService._to_user_response(user, membership, role)

    @staticmethod
    def delete_factory_user(
        db: Session,
        factory_id: uuid.UUID,
        target_user_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
    ) -> dict:
        if target_user_id == actor_user_id:
            raise OperixException(
                message="You cannot delete your own administrator account.",
                status_code=400,
                error_code="CANNOT_DELETE_SELF",
            )

        membership = db.execute(
            select(FactoryMembership).where(
                FactoryMembership.factory_id == factory_id,
                FactoryMembership.user_id == target_user_id,
            )
        ).scalar_one_or_none()
        if membership is None:
            raise ResourceNotFoundException("User", target_user_id)

        db.delete(membership)
        db.flush()

        remaining_memberships = db.execute(
            select(func.count())
            .select_from(FactoryMembership)
            .where(FactoryMembership.user_id == target_user_id)
        ).scalar_one()

        if remaining_memberships == 0:
            tokens = db.execute(select(AuthToken).where(AuthToken.user_id == target_user_id)).scalars().all()
            for tok in tokens:
                db.delete(tok)
            user = db.get(User, target_user_id)
            if user is not None:
                db.delete(user)

        db.flush()
        return {"deleted": True, "user_id": str(target_user_id)}

    # ── Roles & Permissions ───────────────────────────────────────────────────

    @staticmethod
    def list_roles(db: Session) -> List[RoleResponse]:
        roles = db.execute(select(Role).order_by(Role.code.asc())).scalars().all()
        result: List[RoleResponse] = []
        for r in roles:
            perms = (
                db.execute(
                    select(Permission)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == r.id)
                    .order_by(Permission.code.asc())
                )
                .scalars()
                .all()
            )
            result.append(
                RoleResponse(
                    id=r.id,
                    code=r.code,
                    name=r.name,
                    permissions=[PermissionResponse.model_validate(p) for p in perms],
                )
            )
        return result

    @staticmethod
    def get_role(db: Session, role_id: uuid.UUID) -> RoleResponse:
        role = db.get(Role, role_id)
        if role is None:
            raise ResourceNotFoundException("Role", role_id)
        perms = (
            db.execute(
                select(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role.id)
                .order_by(Permission.code.asc())
            )
            .scalars()
            .all()
        )
        return RoleResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            permissions=[PermissionResponse.model_validate(p) for p in perms],
        )

    @staticmethod
    def list_permissions(db: Session) -> List[Permission]:
        return list(db.execute(select(Permission).order_by(Permission.code.asc())).scalars().all())

    @staticmethod
    def assign_membership_role(
        db: Session,
        factory_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role_code: str,
        *,
        actor_role: str,
    ) -> FactoryUserResponse:
        return AdminService.update_factory_user(
            db=db,
            factory_id=factory_id,
            target_user_id=target_user_id,
            update_in=UserUpdateRequest(role_code=role_code),
            actor_role=actor_role,
        )

    # ── Factory Settings ──────────────────────────────────────────────────────

    @staticmethod
    def get_factory(db: Session, factory_id: uuid.UUID) -> Factory:
        factory = db.get(Factory, factory_id)
        if factory is None:
            raise ResourceNotFoundException("Factory", factory_id)
        return factory

    @staticmethod
    def update_factory(
        db: Session,
        factory_id: uuid.UUID,
        update_in: FactorySettingsUpdate,
    ) -> Factory:
        factory = AdminService.get_factory(db, factory_id)
        updates = update_in.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(factory, field, value.strip() if isinstance(value, str) else value)
        factory.updated_at = datetime.now(timezone.utc)
        db.flush()
        db.refresh(factory)
        return factory
