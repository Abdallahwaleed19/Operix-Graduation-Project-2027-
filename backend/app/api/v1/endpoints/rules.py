"""
app/api/v1/endpoints/rules.py
REST API endpoints for Safety Rule Builder and Management.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ....schemas.common import APIResponse, APIResponseMeta
from ....schemas.rules import (
    SafetyRuleCreate,
    SafetyRuleListResponse,
    SafetyRuleResponse,
    SafetyRuleStatusUpdate,
    SafetyRuleUpdate,
)
from ....services.rule_service import RuleService
from ...deps import get_current_factory_id, get_tenant_db

router = APIRouter(prefix="/rules", tags=["Safety Rule Builder"])


@router.post(
    "",
    response_model=APIResponse[SafetyRuleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Safety Rule",
    description="Registers a safety rule scoped to factory, zone, department, or sensor.",
)
def create_rule(
    rule_in: SafetyRuleCreate,
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_tenant_db),
) -> APIResponse[SafetyRuleResponse]:
    """Create a new safety rule with scope exclusivity enforcement."""
    rule = RuleService.create_rule(db=db, factory_id=factory_id, rule_in=rule_in)
    return APIResponse(
        status="success",
        data=SafetyRuleResponse.model_validate(rule),
        meta=APIResponseMeta(factory_id=factory_id),
    )


@router.get(
    "",
    response_model=APIResponse[SafetyRuleListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Safety Rules",
    description="Retrieve all configured safety rules for the tenant factory with optional filters.",
)
def list_rules(
    is_enabled: Optional[bool] = Query(default=None, description="Filter by active state"),
    event_type: Optional[str] = Query(default=None, description="Filter by target event type"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_tenant_db),
) -> APIResponse[SafetyRuleListResponse]:
    """List rules for the tenant."""
    rules, total = RuleService.list_rules(
        db=db,
        factory_id=factory_id,
        is_enabled=is_enabled,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    data = SafetyRuleListResponse(
        items=[SafetyRuleResponse.model_validate(r) for r in rules],
        total=total,
    )
    return APIResponse(
        status="success",
        data=data,
        meta=APIResponseMeta(factory_id=factory_id),
    )


@router.get(
    "/{rule_id}",
    response_model=APIResponse[SafetyRuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Safety Rule by ID",
)
def get_rule(
    rule_id: uuid.UUID,
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_tenant_db),
) -> APIResponse[SafetyRuleResponse]:
    """Retrieve details of a single safety rule."""
    rule = RuleService.get_rule(db=db, factory_id=factory_id, rule_id=rule_id)
    return APIResponse(
        status="success",
        data=SafetyRuleResponse.model_validate(rule),
        meta=APIResponseMeta(factory_id=factory_id),
    )


@router.put(
    "/{rule_id}",
    response_model=APIResponse[SafetyRuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Safety Rule",
    description="Updates safety rule configuration and increments rule version.",
)
def update_rule(
    rule_id: uuid.UUID,
    rule_in: SafetyRuleUpdate,
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_tenant_db),
) -> APIResponse[SafetyRuleResponse]:
    """Update rule configuration."""
    rule = RuleService.update_rule(
        db=db,
        factory_id=factory_id,
        rule_id=rule_id,
        rule_in=rule_in,
    )
    return APIResponse(
        status="success",
        data=SafetyRuleResponse.model_validate(rule),
        meta=APIResponseMeta(factory_id=factory_id),
    )


@router.patch(
    "/{rule_id}/status",
    response_model=APIResponse[SafetyRuleResponse],
    status_code=status.HTTP_200_OK,
    summary="Toggle Safety Rule status",
)
def update_rule_status(
    rule_id: uuid.UUID,
    status_in: SafetyRuleStatusUpdate,
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_tenant_db),
) -> APIResponse[SafetyRuleResponse]:
    """Enable or disable an existing safety rule."""
    rule = RuleService.update_rule_status(
        db=db,
        factory_id=factory_id,
        rule_id=rule_id,
        status_in=status_in,
    )
    return APIResponse(
        status="success",
        data=SafetyRuleResponse.model_validate(rule),
        meta=APIResponseMeta(factory_id=factory_id),
    )


@router.delete(
    "/{rule_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Safety Rule",
)
def delete_rule(
    rule_id: uuid.UUID,
    factory_id: uuid.UUID = Depends(get_current_factory_id),
    db: Session = Depends(get_tenant_db),
) -> APIResponse[dict]:
    """Delete a safety rule."""
    RuleService.delete_rule(db=db, factory_id=factory_id, rule_id=rule_id)
    return APIResponse(
        status="success",
        data={"deleted": True, "rule_id": str(rule_id)},
        meta=APIResponseMeta(factory_id=factory_id),
    )
