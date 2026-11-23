"""
incident_evidence/config.py
Configuration constants for the Incident Evidence module.

All sensitive values are loaded from the .env file at the ai-services root.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the ai-services root
_ENV_FILE = Path(__file__).parent.parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:abdallah@localhost:5432/operix_db",
)

# ---------------------------------------------------------------------------
# Default factory (matches existing seed data)
# ---------------------------------------------------------------------------
DEFAULT_FACTORY_ID: str = os.getenv(
    "DEFAULT_FACTORY_ID",
    "aaaaaaaa-0001-0001-0001-000000000001",
)

# ---------------------------------------------------------------------------
# File storage
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).parent.parent  # backend/ai-services/

EVIDENCE_STORAGE_DIR: Path = Path(
    os.getenv("EVIDENCE_STORAGE_DIR", str(_BASE_DIR / "storage" / "evidence"))
)
EVIDENCE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
MAX_EVIDENCE_SIZE_MB: int = int(os.getenv("MAX_EVIDENCE_SIZE_MB", "100"))
MAX_EVIDENCE_SIZE_BYTES: int = MAX_EVIDENCE_SIZE_MB * 1024 * 1024

# ---------------------------------------------------------------------------
# Allowed MIME types (strictly mapped to PostgreSQL evidence_kind: snapshot, clip)
# ---------------------------------------------------------------------------
ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
})

ALLOWED_VIDEO_TYPES: frozenset[str] = frozenset({
    "video/mp4",
    "video/mpeg",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",  # AVI
})

# Audio evidence is unsupported by the current database schema
UNSUPPORTED_AUDIO_TYPES: frozenset[str] = frozenset({
    "audio/mpeg",       # MP3
    "audio/wav",
    "audio/ogg",
    "audio/webm",
})

ALLOWED_MIME_TYPES: frozenset[str] = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

# MIME-type → kind (must be "snapshot" or "clip" to satisfy DB enum and check constraints)
MIME_TO_KIND: dict[str, str] = {}
for _mime in ALLOWED_IMAGE_TYPES:
    MIME_TO_KIND[_mime] = "snapshot"
for _mime in ALLOWED_VIDEO_TYPES:
    MIME_TO_KIND[_mime] = "clip"

# File extension → MIME type (permissive lookup; real check uses magic bytes)
EXTENSION_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
}

# ---------------------------------------------------------------------------
# Magic-byte signatures for MIME validation
# ---------------------------------------------------------------------------
MAGIC_BYTES: dict[str, bytes] = {
    "image/jpeg":       b"\xff\xd8\xff",
    "image/png":        b"\x89PNG\r\n\x1a\n",
    "image/gif":        b"GIF8",
    "image/webp":       b"RIFF",          # RIFF....WEBP
    "video/mp4":        b"\x00\x00\x00",  # checked by offset 4–8 "ftyp"
    "audio/mpeg":       b"\xff\xfb",
    "audio/wav":        b"RIFF",
}
