"""
app/api/v1/endpoints/roles.py
REST API endpoints for Roles, Permissions, and Membership Role Assignment.
"""
from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ....core.database import get_db, set_tenant_context
from ....core.security import AuthorizationException
from ....schemas.admin import (
    FactoryUserResponse,
    MembershipRoleAssignRequest,
    PermissionResponse,
    RoleListResponse,
    RoleResponse,
)
from ....schemas.common import APIResponse, APIResponseMeta
from ....services.admin_service import AdminService
from ...deps import AuthenticatedUser, get_current_user_context

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])

_ROLE_READ_ROLES = frozenset({"safety_supervisor", "factory_manager", "factory_admin", "platform_admin"})
_ROLE_ADMIN_ROLES = frozenset({"factory_manager", "factory_admin", "platform_admin"})


def _require_role(user: AuthenticatedUser, allowed: frozenset[str], action: str) -> None:
    if user.role.strip().lower() not in allowed:
        raise AuthorizationException(
            f"Insufficient permissions to {action}.",
            error_code="INSUFFICIENT_PERMISSIONS",
        )


def _get_scoped_db(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
) -> Session:
    set_tenant_context(db, factory_id=user.factory_id, user_id=user.user_id)
    return db


@router.get(
    "",
    response_model=APIResponse[RoleListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Canonical Roles",
)
def list_roles(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[RoleListResponse]:
    _require_role(user, _ROLE_READ_ROLES, "list roles")
    roles = AdminService.list_roles(db)
    return APIResponse(
        status="success",
        data=RoleListResponse(items=roles, total=len(roles)),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/permissions",
    response_model=APIResponse[List[PermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Canonical Permissions",
)
def list_permissions(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[List[PermissionResponse]]:
    _require_role(user, _ROLE_READ_ROLES, "list permissions")
    perms = AdminService.list_permissions(db)
    return APIResponse(
        status="success",
        data=[PermissionResponse.model_validate(p) for p in perms],
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{role_id}",
    response_model=APIResponse[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Role Details",
)
def get_role(
    role_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[RoleResponse]:
    _require_role(user, _ROLE_READ_ROLES, "view role details")
    role = AdminService.get_role(db, role_id)
    return APIResponse(
        status="success",
        data=role,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/memberships/{user_id}",
    response_model=APIResponse[FactoryUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Role to Factory Membership",
)
def assign_membership_role(
    user_id: uuid.UUID,
    body: MembershipRoleAssignRequest,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactoryUserResponse]:
    _require_role(user, _ROLE_ADMIN_ROLES, "assign membership roles")
    updated = AdminService.assign_membership_role(
        db,
        user.factory_id,
        user_id,
        body.role_code,
        actor_role=user.role,
    )
    return APIResponse(
        status="success",
        data=updated,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
