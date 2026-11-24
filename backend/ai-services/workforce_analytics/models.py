"""
workforce_analytics/models.py
Canonical SQLAlchemy model re-exports from the main Backend (app.models).

NOTE: The analytics module uses raw SQL via text() in repositories.py and does NOT
duplicate ORM model definitions. All ORM models are owned by backend/app/models/.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.models import (  # noqa: E402, F401
    Base,
    Camera,
    Department,
    Factory,
    FactoryMembership,
    Incident,
    Role,
    UnobservedGap,
    User,
)

__all__ = [
    "Base",
    "Factory",
    "Role",
    "User",
    "FactoryMembership",
    "Department",
    "Camera",
    "UnobservedGap",
    "Incident",
]
