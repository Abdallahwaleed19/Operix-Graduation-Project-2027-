"""
app/core/config.py
Pydantic v2 configuration settings for Operix Main Backend.
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"

# Default storage roots relative to the backend directory (never machine-absolute).
# AI module consumers (Abdullah) should read these names from the environment:
#   EVIDENCE_STORAGE_DIR   — overrides the evidence file storage directory.
#   REPORTS_STORAGE_DIR    — overrides the generated reports storage directory.
_DEFAULT_EVIDENCE_DIR = _BACKEND_DIR / "ai-services" / "storage" / "evidence"
_DEFAULT_REPORTS_DIR  = _BACKEND_DIR / "ai-services" / "storage" / "reports"


class Settings(BaseSettings):
    """Application settings with environment variable override support."""

    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General App Config
    APP_NAME: str = "Operix Industrial AI Safety Platform"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "operix-super-secret-key-change-in-production-32bytes"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # Multi-Tenancy & Security
    DEFAULT_FACTORY_ID: UUID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
    CV_API_KEY_HEADER: str = "X-Camera-Key"
    DEFAULT_CV_API_KEY: str = "operix-cv-cam-default-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ALLOW_TEST_AUTH_FALLBACK: bool = False

    # PostgreSQL Database Configuration
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/operix_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    # Redis Configuration (required for WS ticket feature)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL. Required for WebSocket ticket storage.",
    )
    REDIS_POOL_MAX_CONNECTIONS: int = Field(
        default=10,
        ge=1,
        description="Maximum connections in the async Redis pool.",
    )

    # WebSocket Ticket Configuration
    WS_TICKET_KEY: str = Field(
        ...,
        min_length=32,
        description=(
            "HMAC-SHA256 signing key for WS short-lived tickets. "
            "MUST be separate from SECRET_KEY. Never log this value."
        ),
    )
    WS_TICKET_TTL_SECONDS: int = Field(
        default=30,
        ge=1,
        le=30,
        description="WS ticket validity window in seconds (max 30).",
    )
    WS_MEMBERSHIP_CHECK_INTERVAL: int = Field(
        default=5,
        ge=1,
        description="Seconds between membership revalidation checks on active WS connections.",
    )

    # ---------------------------------------------------------------------------
    # Phase 4 — AI Service Storage Configuration
    # ---------------------------------------------------------------------------
    # Both settings are intentionally expressed as strings (resolved to Path at
    # runtime via the property below) so that pydantic_settings can read them
    # from environment variables without requiring a custom validator.
    #
    # Coordinated setting names (must match what Abdullah's AI modules consume):
    #   EVIDENCE_STORAGE_DIR  →  incident_evidence/config.py  EVIDENCE_STORAGE_DIR
    #   REPORTS_STORAGE_DIR   →  reports_generation/config.py OPERIX_REPORTS_STORAGE_DIR
    EVIDENCE_STORAGE_DIR: Optional[str] = Field(
        default=None,
        description=(
            "Absolute or backend-relative path for evidence file storage. "
            "Env var: EVIDENCE_STORAGE_DIR. "
            "Defaults to <backend>/ai-services/storage/evidence."
        ),
    )
    REPORTS_STORAGE_DIR: Optional[str] = Field(
        default=None,
        description=(
            "Absolute or backend-relative path for generated reports storage. "
            "Env var: REPORTS_STORAGE_DIR. "
            "Defaults to <backend>/ai-services/storage/reports."
        ),
    )

    @model_validator(mode="after")
    def _resolve_storage_dirs(self) -> "Settings":
        """
        Resolve storage directory paths and ensure they exist.
        Called once after all fields are populated.
        Does NOT move or delete existing data.
        """
        def _resolve(raw: Optional[str], default: Path) -> Path:
            p = Path(raw) if raw else default
            if not p.is_absolute():
                p = _BACKEND_DIR / p
            try:
                p.mkdir(parents=True, exist_ok=True)
            except OSError:
                # Non-fatal: directory may be a network mount not yet available.
                pass
            return p

        self._evidence_storage_path: Path = _resolve(
            self.EVIDENCE_STORAGE_DIR, _DEFAULT_EVIDENCE_DIR
        )
        self._reports_storage_path: Path = _resolve(
            self.REPORTS_STORAGE_DIR, _DEFAULT_REPORTS_DIR
        )
        return self

    @property
    def evidence_storage_path(self) -> Path:
        """Resolved, guaranteed-absolute evidence storage directory."""
        return self._evidence_storage_path

    @property
    def reports_storage_path(self) -> Path:
        """Resolved, guaranteed-absolute reports storage directory."""
        return self._reports_storage_path

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    def __repr__(self) -> str:
        """Never expose secret values in repr."""
        return (
            f"Settings(APP_NAME={self.APP_NAME!r}, APP_ENV={self.APP_ENV!r}, "
            f"DATABASE_URL=<redacted>, REDIS_URL=<redacted>, "
            f"WS_TICKET_KEY=<redacted>, SECRET_KEY=<redacted>)"
        )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            raw = v.strip()
            if raw.startswith("["):
                import json
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed if str(i).strip()]
                except Exception:
                    pass
            return [i.strip() for i in raw.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


settings = get_settings()
