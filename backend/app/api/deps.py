"""
app/api/deps.py
FastAPI dependency injection utilities for DB sessions and tenant context.
"""
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db, set_tenant_context


def get_current_factory_id(
    x_factory_id: Optional[str] = Header(
        default=None,
        description="Tenant Factory UUID (optional, defaults to configured factory)",
    ),
) -> UUID:
    """Extract factory_id from request header or fall back to default."""
    if x_factory_id:
        try:
            return UUID(x_factory_id)
        except ValueError:
            pass
    return settings.DEFAULT_FACTORY_ID


def get_tenant_db(
    db: Session = Depends(get_db),
    factory_id: UUID = Depends(get_current_factory_id),
) -> Generator[Session, None, None]:
    """
    Yields an active DB session with Row-Level Security (RLS) tenant context set.
    """
    set_tenant_context(db, factory_id=factory_id)
    try:
        yield db
    finally:
        pass
