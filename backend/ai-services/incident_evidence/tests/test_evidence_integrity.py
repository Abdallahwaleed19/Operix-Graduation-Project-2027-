"""
incident_evidence/tests/test_evidence_integrity.py
Unit tests for EvidenceIntegrityService.
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from incident_evidence.exceptions import StorageError
from incident_evidence.schemas import EvidenceFileRecord, EvidenceKind
from incident_evidence.services.evidence_integrity_service import EvidenceIntegrityService
from incident_evidence.storage.local_storage import LocalStorage

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
EVENT_ID = UUID("bbbbbbbb-0001-0001-0001-000000000001")


def _make_record(storage_key: str, sha256: str = None) -> EvidenceFileRecord:
    return EvidenceFileRecord(
        id=uuid4(),
        factory_id=FACTORY_ID,
        event_id=EVENT_ID,
        kind=EvidenceKind.IMAGE,
        storage_key=storage_key,
        content_type="image/jpeg",
        size_bytes=100,
        sha256=sha256,
        captured_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
    )


class TestEvidenceIntegrityService(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = LocalStorage(Path(self.tmp))
        self.svc = EvidenceIntegrityService(storage=self.storage)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_file(self, key: str, data: bytes) -> str:
        self.storage.save(key, data)
        return hashlib.sha256(data).hexdigest()

    def test_integrity_ok(self):
        data = b"test evidence data"
        sha256 = self._write_file("factory/event/evidence.jpg", data)
        record = _make_record("factory/event/evidence.jpg", sha256=sha256)

        conn = MagicMock()
        with unittest.mock.patch(
            "incident_evidence.services.evidence_integrity_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            result = self.svc.verify(conn, record.id, FACTORY_ID)

        self.assertTrue(result.integrity_ok)
        self.assertEqual(result.computed_sha256, sha256)
        self.assertIn("matches", result.message.lower())

    def test_integrity_mismatch(self):
        data = b"original data"
        corrupted = b"corrupted!!"
        good_sha = hashlib.sha256(data).hexdigest()
        # Save corrupted file but record has good hash
        self.storage.save("factory/event/bad.jpg", corrupted)
        record = _make_record("factory/event/bad.jpg", sha256=good_sha)

        conn = MagicMock()
        with unittest.mock.patch(
            "incident_evidence.services.evidence_integrity_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            result = self.svc.verify(conn, record.id, FACTORY_ID)

        self.assertFalse(result.integrity_ok)
        self.assertIn("FAILURE", result.message.upper())

    def test_no_stored_hash(self):
        data = b"no hash stored"
        self.storage.save("factory/event/nohash.jpg", data)
        record = _make_record("factory/event/nohash.jpg", sha256=None)

        conn = MagicMock()
        with unittest.mock.patch(
            "incident_evidence.services.evidence_integrity_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            result = self.svc.verify(conn, record.id, FACTORY_ID)

        self.assertTrue(result.integrity_ok)
        self.assertIsNone(result.stored_sha256)
        self.assertIsNotNone(result.computed_sha256)

    def test_file_missing_raises(self):
        record = _make_record("factory/event/missing.jpg", sha256="a" * 64)

        conn = MagicMock()
        with unittest.mock.patch(
            "incident_evidence.services.evidence_integrity_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            with self.assertRaises(StorageError):
                self.svc.verify(conn, record.id, FACTORY_ID)

    def test_result_has_evidence_id(self):
        data = b"check id"
        sha256 = self._write_file("factory/event/checkid.jpg", data)
        record = _make_record("factory/event/checkid.jpg", sha256=sha256)

        conn = MagicMock()
        with unittest.mock.patch(
            "incident_evidence.services.evidence_integrity_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            result = self.svc.verify(conn, record.id, FACTORY_ID)

        self.assertEqual(result.evidence_id, record.id)
        self.assertIsNotNone(result.verified_at)


import unittest.mock  # noqa: E402


if __name__ == "__main__":
    unittest.main()
