"""
schemas/contracts.py
Core Pydantic v2 data contracts for Ingestion, Retrieval, and Assistant interfaces.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentSourceType(str, Enum):
    """Categorization of ingested knowledge sources."""
    DATABASE_SAFETY_RULE = "db_safety_rule"
    DATABASE_INCIDENT = "db_incident"
    DATABASE_CAMERA = "db_camera"
    DATABASE_ZONE = "db_monitoring_zone"
    DATABASE_DEPARTMENT = "db_department"
    DATABASE_FACTORY = "db_factory"
    MANUAL_PDF = "manual_pdf"
    MANUAL_MARKDOWN = "manual_markdown"
    MANUAL_TEXT = "manual_text"


class ChunkMetadata(BaseModel):
    """Contextual metadata attached to each document chunk."""
    chunk_id: str = Field(description="Unique identifier of chunk (e.g., hash or uuid).")
    source_id: str = Field(description="ID of source entity or file path.")
    source_title: str = Field(description="Human readable title or filename.")
    source_type: DocumentSourceType = Field(description="Origin category.")
    factory_id: Optional[UUID] = Field(default=None, description="Scoped factory ID if applicable.")
    department_id: Optional[UUID] = Field(default=None, description="Department ID if applicable.")
    page_number: Optional[int] = Field(default=None, description="Page number for PDF documents.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    extra: dict[str, Any] = Field(default_factory=dict, description="Arbitrary safe metadata attributes.")


class DocumentChunk(BaseModel):
    """Atomic unit of ingested text ready for embedding and retrieval."""
    content: str = Field(description="Textual chunk content.")
    metadata: ChunkMetadata = Field(description="Associated metadata.")
    token_estimate: Optional[int] = Field(default=None, description="Estimated token count.")


class IngestionSummary(BaseModel):
    """Result summary of an ingestion pipeline run."""
    total_documents_scanned: int = 0
    total_chunks_created: int = 0
    sources_ingested: list[str] = Field(default_factory=list)
    skipped_documents: int = 0
    duration_seconds: float = 0.0
    status: str = "completed"


class RetrievalFilter(BaseModel):
    """Granular search filter to enforce tenant isolation and relevance."""
    factory_id: Optional[UUID] = Field(default=None, description="Mandatory tenant scope when available.")
    department_id: Optional[UUID] = Field(default=None, description="Optional department scope.")
    source_types: Optional[List[DocumentSourceType]] = Field(default=None, description="Allowed source types.")
    top_k: int = Field(default=5, ge=1, le=25, description="Number of chunks to return.")
    min_similarity: float = Field(default=0.60, ge=0.0, le=1.0, description="Cosine similarity threshold.")


class RetrievedChunk(BaseModel):
    """Single matching chunk with similarity score."""
    content: str
    metadata: ChunkMetadata
    similarity_score: float = Field(ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    """Result set returned by the vector retrieval engine."""
    query: str
    chunks: List[RetrievedChunk] = Field(default_factory=list)
    has_sufficient_evidence: bool = Field(default=False)
    retrieval_latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Assistant Request & Response Contracts
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    """Verified user identity passed from future FastAPI auth dependency."""
    user_id: UUID
    full_name: str
    role_code: str  # e.g., 'factory_admin', 'factory_manager', 'safety_supervisor'
    factory_id: UUID


class AssistantQueryRequest(BaseModel):
    """Input query to the LLM/RAG assistant."""
    question: str = Field(min_length=2, max_length=1000, description="User's query in Arabic or English.")
    conversation_id: Optional[str] = Field(default=None, description="Session ID to track conversation history.")
    user_context: Optional[UserContext] = Field(default=None, description="Security and tenant context.")
    language_preference: Literal["auto", "ar", "en"] = Field(default="auto")


class SourceCitation(BaseModel):
    """Source attribution for verified facts."""
    source_title: str
    source_type: str
    source_id: str
    snippet: str
    page_number: Optional[int] = None
    similarity_score: Optional[float] = None


class AssistantQueryResponse(BaseModel):
    """Ground-truth output from the LLM/RAG assistant."""
    answer: str
    conversation_id: str
    has_sufficient_evidence: bool
    citations: List[SourceCitation] = Field(default_factory=list)
    provider: str  # 'openai' | 'ollama' | 'mock'
    model_name: str
    language: str  # 'ar' | 'en'
    processing_time_seconds: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
