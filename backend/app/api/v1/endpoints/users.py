"""
app/api/v1/endpoints/users.py
REST API endpoints for tenant-scoped User & Membership management.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ....core.database import get_db, set_tenant_context
from ....core.security import AuthorizationException
from ....schemas.admin import (
    FactoryUserListResponse,
    FactoryUserResponse,
    UserInviteRequest,
    UserUpdateRequest,
)
from ....schemas.common import APIResponse, APIResponseMeta
from ....services.admin_service import AdminService
from ...deps import AuthenticatedUser, get_current_user_context

router = APIRouter(prefix="/users", tags=["Users & Memberships"])

_USER_READ_ROLES = frozenset({"safety_supervisor", "factory_manager", "factory_admin", "platform_admin"})
_USER_ADMIN_ROLES = frozenset({"factory_manager", "factory_admin", "platform_admin"})


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
    response_model=APIResponse[FactoryUserListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Users in Current Factory",
)
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactoryUserListResponse]:
    _require_role(user, _USER_READ_ROLES, "list users")
    items, total = AdminService.list_factory_users(db, user.factory_id, limit=limit, offset=offset)
    return APIResponse(
        status="success",
        data=FactoryUserListResponse(items=items, total=total),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[FactoryUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Details in Current Factory",
)
def get_user(
    user_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactoryUserResponse]:
    _require_role(user, _USER_READ_ROLES, "view user details")
    target = AdminService.get_factory_user(db, user.factory_id, user_id)
    return APIResponse(
        status="success",
        data=target,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.post(
    "/invite",
    response_model=APIResponse[FactoryUserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite User to Current Factory",
)
def invite_user(
    invite_in: UserInviteRequest,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactoryUserResponse]:
    _require_role(user, _USER_ADMIN_ROLES, "invite users")
    created = AdminService.invite_user(db, user.factory_id, invite_in, actor_role=user.role)
    return APIResponse(
        status="success",
        data=created,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/{user_id}",
    response_model=APIResponse[FactoryUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Factory User & Membership",
)
def update_user(
    user_id: uuid.UUID,
    update_in: UserUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactoryUserResponse]:
    _require_role(user, _USER_ADMIN_ROLES, "update users")
    updated = AdminService.update_factory_user(
        db,
        user.factory_id,
        user_id,
        update_in,
        actor_role=user.role,
    )
    return APIResponse(
        status="success",
        data=updated,
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
