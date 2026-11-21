"""
ingestion/document_loader.py
Extracts text and page-level metadata from PDF, Markdown, and TXT files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from ..schemas.contracts import DocumentSourceType
from .text_processor import clean_text


class RawDocument:
    """Intermediate container for loaded document text and its raw metadata."""

    def __init__(
        self,
        content: str,
        source_id: str,
        source_title: str,
        source_type: DocumentSourceType,
        page_number: Optional[int] = None,
        factory_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
    ) -> None:
        self.content = content
        self.source_id = source_id
        self.source_title = source_title
        self.source_type = source_type
        self.page_number = page_number
        self.factory_id = factory_id
        self.department_id = department_id


class DocumentLoader:
    """Multi-format file document loader."""

    def load_pdf(
        self,
        file_path: Path | str,
        factory_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
    ) -> List[RawDocument]:
        """Extract text page by page from a PDF file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        documents: List[RawDocument] = []
        source_id = path.name
        source_title = path.stem.replace("_", " ").title()

        # Try PyMuPDF (fitz) first for fastest and cleanest extraction
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            for page_idx, page in enumerate(doc, 1):
                text = clean_text(page.get_text("text"))
                if text:
                    documents.append(
                        RawDocument(
                            content=text,
                            source_id=source_id,
                            source_title=source_title,
                            source_type=DocumentSourceType.MANUAL_PDF,
                            page_number=page_idx,
                            factory_id=factory_id,
                            department_id=department_id,
                        )
                    )
            return documents
        except ImportError:
            pass

        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            for page_idx, page in enumerate(reader.pages, 1):
                text = clean_text(page.extract_text() or "")
                if text:
                    documents.append(
                        RawDocument(
                            content=text,
                            source_id=source_id,
                            source_title=source_title,
                            source_type=DocumentSourceType.MANUAL_PDF,
                            page_number=page_idx,
                            factory_id=factory_id,
                            department_id=department_id,
                        )
                    )
            return documents
        except Exception as exc:
            raise RuntimeError(f"Failed to read PDF {path}: {exc}") from exc

    def load_text(
        self,
        file_path: Path | str,
        factory_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
    ) -> List[RawDocument]:
        """Load text from a .txt or .md file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = clean_text(path.read_text(encoding="utf-8", errors="replace"))
        if not content:
            return []

        ext = path.suffix.lower()
        source_type = (
            DocumentSourceType.MANUAL_MARKDOWN if ext == ".md" else DocumentSourceType.MANUAL_TEXT
        )

        return [
            RawDocument(
                content=content,
                source_id=path.name,
                source_title=path.stem.replace("_", " ").title(),
                source_type=source_type,
                page_number=1,
                factory_id=factory_id,
                department_id=department_id,
            )
        ]

    def load_directory(
        self,
        directory: Path | str,
        factory_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
    ) -> List[RawDocument]:
        """Scan a directory and load all supported documents (.pdf, .md, .txt)."""
        dir_path = Path(directory)
        if not dir_path.exists():
            return []

        all_docs: List[RawDocument] = []
        for file in dir_path.glob("**/*"):
            if file.is_file():
                ext = file.suffix.lower()
                try:
                    if ext == ".pdf":
                        all_docs.extend(self.load_pdf(file, factory_id, department_id))
                    elif ext in (".md", ".txt"):
                        all_docs.extend(self.load_text(file, factory_id, department_id))
                except Exception as exc:
                    print(f"[DocumentLoader] Skipped file {file.name}: {exc}")
        return all_docs
