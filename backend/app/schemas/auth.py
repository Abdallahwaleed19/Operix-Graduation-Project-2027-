"""
app/schemas/auth.py
Pydantic schemas for human authentication endpoints (/api/v1/auth/*).
"""
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254, description="User email address.")
    password: str = Field(..., min_length=1, max_length=256, description="Plaintext password.")
    factory_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional target factory UUID when user belongs to multiple factories.",
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, description="Opaque refresh token.")
    factory_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional target factory UUID when refreshing.",
    )


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, description="Refresh token to revoke.")


class AuthUserSummary(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    factory_id: uuid.UUID
    factory_name: str


class LoginData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserSummary


class MeData(BaseModel):
    user_id: uuid.UUID
    factory_id: uuid.UUID
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None


class LogoutData(BaseModel):
    revoked: bool
