"""
incident_evidence/tests/test_evidence_upload.py
Unit tests for EvidenceUploadService.
Uses in-memory mock DB and temp filesystem — never touches real DB.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from incident_evidence.exceptions import (
    EvidenceTransactionError,
    FileSizeLimitError,
    InvalidEvidenceTypeError,
    InvalidMimeTypeError,
)
from incident_evidence.schemas import EvidenceKind, EvidenceUploadRequest
from incident_evidence.services.evidence_upload_service import EvidenceUploadService
from incident_evidence.storage.local_storage import LocalStorage

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
EVENT_ID = UUID("bbbbbbbb-0001-0001-0001-000000000001")


def _make_request(**kwargs) -> EvidenceUploadRequest:
    defaults = dict(
        factory_id=FACTORY_ID,
        event_id=EVENT_ID,
        captured_at=datetime.now(tz=timezone.utc),
    )
    defaults.update(kwargs)
    return EvidenceUploadRequest(**defaults)


def _make_fake_record(storage_key: str, kind: EvidenceKind = EvidenceKind.SNAPSHOT):
    """Return a minimal mock EvidenceFileRecord."""
    record = MagicMock()
    record.id = uuid4()
    record.factory_id = FACTORY_ID
    record.event_id = EVENT_ID
    record.kind = kind
    record.storage_key = storage_key
    record.content_type = "image/jpeg"
    record.size_bytes = 100
    record.sha256 = "a" * 64
    record.duration_s = None
    record.captured_at = datetime.now(tz=timezone.utc)
    record.expires_at = None
    record.purged_at = None
    record.created_at = datetime.now(tz=timezone.utc)
    return record


class TestEvidenceUploadServiceValidation(unittest.TestCase):
    """Tests for validation logic (no real storage needed)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = LocalStorage(Path(self.tmp))
        self.svc = EvidenceUploadService(storage=self.storage)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_invalid_mime_type(self):
        conn = MagicMock()
        with self.assertRaises(InvalidMimeTypeError):
            self.svc.upload(conn, _make_request(), b"data", "application/pdf")

    def test_file_too_large(self):
        conn = MagicMock()
        big_bytes = b"x" * (101 * 1024 * 1024)  # 101 MB
        with self.assertRaises(FileSizeLimitError):
            self.svc.upload(conn, _make_request(), big_bytes, "image/jpeg")

    def test_zero_byte_file_rejected(self):
        """Zero-byte file must fail validation (PostgreSQL check constraint size_bytes > 0)."""
        conn = MagicMock()
        with self.assertRaises(FileSizeLimitError):
            self.svc.upload(conn, _make_request(), b"", "image/jpeg")

    def test_valid_image_upload(self):
        """Happy path: image upload succeeds, DB record created."""
        image_bytes = b"\xff\xd8\xff" + b"\x00" * 100  # minimal JPEG magic
        conn = MagicMock()
        storage_key_capture = {}

        def mock_create_record(**kwargs):
            storage_key_capture["key"] = kwargs["storage_key"]
            return _make_fake_record(kwargs["storage_key"], kind=EvidenceKind.SNAPSHOT)

        with patch(
            "incident_evidence.services.evidence_upload_service.EvidenceRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_record.side_effect = mock_create_record
            record = self.svc.upload(conn, _make_request(), image_bytes, "image/jpeg")

        self.assertEqual(record.kind, EvidenceKind.SNAPSHOT)
        key = storage_key_capture["key"]
        self.assertTrue(key.startswith(f"f/{FACTORY_ID}/"))
        self.assertTrue(self.storage.exists(key))

    def test_sha256_computed_correctly(self):
        """SHA-256 passed to repo matches file bytes."""
        image_bytes = b"\xff\xd8\xff" + b"\x00" * 50
        expected_hash = hashlib.sha256(image_bytes).hexdigest()
        conn = MagicMock()
        captured_hash = {}

        def mock_create_record(**kwargs):
            captured_hash["sha256"] = kwargs["sha256"]
            return _make_fake_record(kwargs["storage_key"])

        with patch(
            "incident_evidence.services.evidence_upload_service.EvidenceRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_record.side_effect = mock_create_record
            self.svc.upload(conn, _make_request(), image_bytes, "image/jpeg")

        self.assertEqual(captured_hash["sha256"], expected_hash)

    def test_db_failure_rolls_back_file(self):
        """If DB INSERT fails, the saved file must be deleted."""
        image_bytes = b"\xff\xd8\xff" + b"\x00" * 50
        conn = MagicMock()
        saved_key = {}

        original_save = self.storage.save

        def tracking_save(key, data):
            saved_key["key"] = key
            return original_save(key, data)

        self.storage.save = tracking_save

        with patch(
            "incident_evidence.services.evidence_upload_service.EvidenceRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_record.side_effect = EvidenceTransactionError("DB error")
            with self.assertRaises(EvidenceTransactionError):
                self.svc.upload(conn, _make_request(), image_bytes, "image/jpeg")

        # File should have been rolled back
        if "key" in saved_key:
            self.assertFalse(self.storage.exists(saved_key["key"]))

    def test_video_upload_with_duration(self):
        """Video clips with valid duration and ftyp magic succeed."""
        conn = MagicMock()
        video_bytes = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 50
        req = _make_request(duration_s=12.5)

        with patch(
            "incident_evidence.services.evidence_upload_service.EvidenceRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_record.return_value = _make_fake_record("f/test/video.mp4", kind=EvidenceKind.CLIP)
            record = self.svc.upload(conn, req, video_bytes, "video/mp4")
        self.assertEqual(record.kind, EvidenceKind.CLIP)

    def test_video_missing_duration_rejected(self):
        """Video clips without duration_s fail (DB check constraint kind = snapshot OR duration_s IS NOT NULL)."""
        conn = MagicMock()
        video_bytes = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 50
        req = _make_request(duration_s=None)

        with self.assertRaises(InvalidEvidenceTypeError):
            self.svc.upload(conn, req, video_bytes, "video/mp4")

    def test_audio_upload_rejected(self):
        """Audio evidence is rejected per database schema constraints."""
        conn = MagicMock()
        with self.assertRaises(InvalidMimeTypeError):
            self.svc.upload(conn, _make_request(), b"\xff\xfb\x90\x44" + b"\x00" * 50, "audio/mpeg")


if __name__ == "__main__":
    unittest.main()
