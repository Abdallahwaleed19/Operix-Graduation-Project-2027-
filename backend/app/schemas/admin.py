"""
app/schemas/admin.py
Pydantic schemas for S-4 Users, Roles/Permissions, and Factory Settings APIs.
Explicitly excludes password hashes, token hashes, and private auth metadata.
"""
from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import FactoryStatus, UserStatus


class FactoryUserResponse(BaseModel):
    user_id: uuid.UUID
    factory_id: uuid.UUID
    email: str
    full_name: str
    status: UserStatus
    role_id: uuid.UUID
    role_code: str
    role_name: str
    membership_active: bool
    activated_at: Optional[datetime] = None
    created_at: datetime


class FactoryUserListResponse(BaseModel):
    items: List[FactoryUserResponse]
    total: int


class UserInviteRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    full_name: str = Field(..., min_length=1, max_length=120)
    role_code: str = Field(..., min_length=1, max_length=40)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    status: Optional[UserStatus] = None
    membership_active: Optional[bool] = None
    role_code: Optional[str] = Field(default=None, min_length=1, max_length=40)


class MembershipRoleAssignRequest(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=40)


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: str


class RoleResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    permissions: List[PermissionResponse] = []


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
    total: int


class FactorySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: FactoryStatus
    timezone: str
    evidence_retention_days: int
    created_at: datetime
    updated_at: datetime


class FactorySettingsUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=40)
    evidence_retention_days: Optional[int] = Field(default=None, ge=1)
