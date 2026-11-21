"""
tests/test_ingestion.py
Unit and integration tests for the Knowledge Ingestion Pipeline.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from ..ingestion.chunker import DocumentChunker
from ..ingestion.database_loader import DatabaseKnowledgeLoader
from ..ingestion.document_loader import DocumentLoader
from ..ingestion.metadata import compute_chunk_hash
from ..ingestion.pipeline import KnowledgeIngestionPipeline
from ..ingestion.text_processor import clean_text, detect_language
from ..schemas.contracts import DocumentSourceType


class TestTextProcessor(unittest.TestCase):
    def test_clean_text_normalizes_whitespace(self):
        raw = "  Hello   world \n\n\n\n  from \t\t Operix! \r\n"
        cleaned = clean_text(raw)
        self.assertEqual(cleaned, "Hello world \n\n from Operix!")

    def test_detect_language(self):
        self.assertEqual(detect_language("This is an industrial safety rule."), "en")
        self.assertEqual(detect_language("يجب على جميع العمال ارتداء خوذة الأمان داخل المصنع."), "ar")
        self.assertEqual(detect_language(""), "en")


class TestDocumentChunker(unittest.TestCase):
    def test_chunk_size_validation(self):
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=0)
        with self.assertRaises(ValueError):
            DocumentChunker(chunk_size=100, chunk_overlap=100)

    def test_short_text_single_chunk(self):
        chunker = DocumentChunker(chunk_size=300, chunk_overlap=50)
        chunks = chunker.chunk_text(
            text="Wear safety glasses in the welding area.",
            source_id="sop-1",
            source_title="PPE Rule",
            source_type=DocumentSourceType.MANUAL_TEXT,
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, "Wear safety glasses in the welding area.")
        self.assertIn("chk_", chunks[0].metadata.chunk_id)

    def test_sentence_boundary_preservation(self):
        chunker = DocumentChunker(chunk_size=120, chunk_overlap=30)
        text = (
            "Rule one: always wear protective boots. "
            "Rule two: keep your hands clear of moving belts. "
            "Rule three: report all chemical leaks immediately. "
            "Rule four: do not enter restricted welding zones without supervisor permit."
        )
        chunks = chunker.chunk_text(
            text=text,
            source_id="rules-all",
            source_title="Safety Rules Overview",
            source_type=DocumentSourceType.MANUAL_TEXT,
        )
        self.assertGreater(len(chunks), 1)
        # Ensure chunks do not terminate in the middle of words
        for c in chunks:
            self.assertTrue(c.content[-1] in ".!?" or c.content[-1].isalnum())

    def test_deduplication_hash(self):
        h1 = compute_chunk_hash("Safety guideline content.", "doc-01", 1)
        h2 = compute_chunk_hash("Safety guideline content.", "doc-01", 1)
        h3 = compute_chunk_hash("Different guideline content.", "doc-01", 1)
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)


class TestDocumentLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DocumentLoader()

    def test_load_text_file(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# Safety Protocol\n\nMandatory eye protection in effect.")
            temp_path = f.name

        try:
            docs = self.loader.load_text(temp_path)
            self.assertEqual(len(docs), 1)
            self.assertIn("Mandatory eye protection", docs[0].content)
            self.assertEqual(docs[0].source_type, DocumentSourceType.MANUAL_MARKDOWN)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_nonexistent_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            self.loader.load_text("non_existent_file_12345.txt")


class TestDatabaseLoaderIntegration(unittest.TestCase):
    def setUp(self):
        self.loader = DatabaseKnowledgeLoader()

    def test_extract_safety_rules(self):
        docs = self.loader.extract_safety_rules()
        self.assertIsInstance(docs, list)
        self.assertGreaterEqual(len(docs), 3)  # At least the 3 seeded rules
        first = docs[0]
        self.assertIn("Safety Rule:", first.content)
        self.assertEqual(first.source_type, DocumentSourceType.DATABASE_SAFETY_RULE)

    def test_extract_incidents(self):
        docs = self.loader.extract_incidents(limit=10)
        self.assertIsInstance(docs, list)
        self.assertGreaterEqual(len(docs), 5)
        self.assertIn("Incident Record:", docs[0].content)

    def test_extract_cameras(self):
        docs = self.loader.extract_cameras_and_downtime()
        self.assertIsInstance(docs, list)
        self.assertEqual(len(docs), 4)


class TestIngestionPipelineIntegration(unittest.TestCase):
    def test_pipeline_run(self):
        pipeline = KnowledgeIngestionPipeline(chunk_size=400, chunk_overlap=80)
        sample_doc_dir = Path(__file__).resolve().parent.parent / "data" / "documents"

        chunks, summary = pipeline.run(
            documents_dir=sample_doc_dir,
            include_database=True,
        )
        self.assertGreater(len(chunks), 10)
        self.assertEqual(summary.status, "completed")
        self.assertGreater(summary.total_chunks_created, 0)
        self.assertGreater(summary.total_documents_scanned, 0)

        # Check metadata on generated chunks
        source_types = {c.metadata.source_type for c in chunks}
        self.assertIn(DocumentSourceType.DATABASE_SAFETY_RULE, source_types)
        self.assertIn(DocumentSourceType.DATABASE_INCIDENT, source_types)


if __name__ == "__main__":
    unittest.main(verbosity=2)
