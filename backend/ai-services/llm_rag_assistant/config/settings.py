"""
config/settings.py
Centralized configuration for the Operix LLM/RAG Assistant.

Loads configuration from environment variables and .env files with sensible defaults.
Supports dynamic switching between Cloud (OpenAI) and Local (Ollama) providers.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Locate .env: check current module directory, then parent ai-services directory
_MODULE_DIR = Path(__file__).resolve().parent.parent
_AI_SERVICES_DIR = _MODULE_DIR.parent

_ENV_PATHS = [
    _MODULE_DIR / ".env",
    _AI_SERVICES_DIR / ".env",
    _AI_SERVICES_DIR.parent.parent / ".env",
]

for p in _ENV_PATHS:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break


class AssistantSettings(BaseModel):
    """Configuration settings for LLM RAG Assistant."""

    # -----------------------------------------------------------------------
    # Environment & Factory Scope
    # -----------------------------------------------------------------------
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    default_factory_id: UUID = Field(
        default_factory=lambda: UUID(
            os.getenv("DEFAULT_FACTORY_ID", os.getenv("OPERIX_FACTORY_ID", "aaaaaaaa-0001-0001-0001-000000000001"))
        )
    )

    # -----------------------------------------------------------------------
    # Database Settings (Read-Only Operational Access)
    # -----------------------------------------------------------------------
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:abdallah@localhost:5432/operix_db"
        )
    )

    # -----------------------------------------------------------------------
    # AI Provider Modes
    # -----------------------------------------------------------------------
    llm_provider: Literal["openai", "ollama", "mock"] = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openai").lower()  # type: ignore
    )
    embedding_provider: Literal["openai", "ollama", "mock"] = Field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "openai").lower()  # type: ignore
    )

    # -----------------------------------------------------------------------
    # Cloud Provider: OpenAI
    # -----------------------------------------------------------------------
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    openai_chat_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )
    openai_embedding_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    openai_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30.0"))
    )

    # -----------------------------------------------------------------------
    # Local Provider: Ollama
    # -----------------------------------------------------------------------
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_chat_model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
    )
    ollama_embedding_model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    )
    ollama_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60.0"))
    )

    # -----------------------------------------------------------------------
    # Ingestion & Chunking
    # -----------------------------------------------------------------------
    chunk_size: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_SIZE", "500"))
    )
    chunk_overlap: int = Field(
        default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "100"))
    )
    max_document_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("MAX_DOCUMENT_SIZE_MB", "25"))
    )

    # -----------------------------------------------------------------------
    # Retrieval & Vector Storage
    # -----------------------------------------------------------------------
    vector_store_type: Literal["numpy_local", "sqlite_vec", "chroma"] = Field(
        default_factory=lambda: os.getenv("VECTOR_STORE_TYPE", "numpy_local").lower()  # type: ignore
    )
    vector_store_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("VECTOR_STORE_DIR", str(_MODULE_DIR / "data" / "vector_store"))
        )
    )
    top_k: int = Field(
        default_factory=lambda: int(os.getenv("RETRIEVAL_TOP_K", "5"))
    )
    similarity_threshold: float = Field(
        default_factory=lambda: float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))
    )

    # -----------------------------------------------------------------------
    # Guardrails & Conversation
    # -----------------------------------------------------------------------
    strict_grounding: bool = Field(
        default_factory=lambda: os.getenv("STRICT_GROUNDING", "true").lower() == "true"
    )
    max_history_turns: int = Field(
        default_factory=lambda: int(os.getenv("MAX_HISTORY_TURNS", "6"))
    )


@lru_cache()
def get_settings() -> AssistantSettings:
    """Return cached singleton instance of AssistantSettings."""
    return AssistantSettings()
