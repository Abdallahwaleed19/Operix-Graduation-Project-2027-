"""
app/api/v1/endpoints/factories.py
REST API endpoints for tenant-scoped Factory Settings.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ....core.database import get_db, set_tenant_context
from ....core.security import AuthorizationException
from ....schemas.admin import FactorySettingsResponse, FactorySettingsUpdate
from ....schemas.common import APIResponse, APIResponseMeta
from ....services.admin_service import AdminService
from ...deps import AuthenticatedUser, get_current_user_context

router = APIRouter(prefix="/factories", tags=["Factory Settings"])

_FACTORY_ADMIN_ROLES = frozenset({"factory_manager", "factory_admin", "platform_admin"})


def _get_scoped_db(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
) -> Session:
    set_tenant_context(db, factory_id=user.factory_id, user_id=user.user_id)
    return db


@router.get(
    "/current",
    response_model=APIResponse[FactorySettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Current Factory Settings",
)
def get_current_factory(
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactorySettingsResponse]:
    factory = AdminService.get_factory(db, user.factory_id)
    return APIResponse(
        status="success",
        data=FactorySettingsResponse.model_validate(factory),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )


@router.patch(
    "/current",
    response_model=APIResponse[FactorySettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Current Factory Settings",
)
def update_current_factory(
    update_in: FactorySettingsUpdate,
    user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(_get_scoped_db),
) -> APIResponse[FactorySettingsResponse]:
    if user.role.strip().lower() not in _FACTORY_ADMIN_ROLES:
        raise AuthorizationException(
            "Insufficient permissions to update factory settings.",
            error_code="INSUFFICIENT_PERMISSIONS",
        )
    factory = AdminService.update_factory(db, user.factory_id, update_in)
    return APIResponse(
        status="success",
        data=FactorySettingsResponse.model_validate(factory),
        meta=APIResponseMeta(factory_id=user.factory_id),
    )
