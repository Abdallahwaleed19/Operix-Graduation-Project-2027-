"""
ingestion package for Operix LLM/RAG Assistant.
"""
from .chunker import DocumentChunker
from .database_loader import DatabaseKnowledgeLoader
from .document_loader import DocumentLoader, RawDocument
from .metadata import compute_chunk_hash, create_metadata
from .pipeline import KnowledgeIngestionPipeline
from .text_processor import clean_text, detect_language

__all__ = [
    "clean_text",
    "detect_language",
    "compute_chunk_hash",
    "create_metadata",
    "DocumentChunker",
    "RawDocument",
    "DocumentLoader",
    "DatabaseKnowledgeLoader",
    "KnowledgeIngestionPipeline",
]
