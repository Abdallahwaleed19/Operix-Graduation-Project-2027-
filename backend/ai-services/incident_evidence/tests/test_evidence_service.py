"""
incident_evidence/tests/test_evidence_service.py
Integration-style unit tests for the EvidenceService facade.
Uses mocks — never touches real DB or real filesystem beyond tempdir.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from incident_evidence.schemas import (
    EvidenceKind,
    EvidenceFileRecord,
    EvidenceListResponse,
    EvidenceMetadataResponse,
    EvidenceUploadRequest,
    IntegrityVerificationResult,
)
from incident_evidence.services.evidence_service import EvidenceService

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
EVENT_ID = UUID("bbbbbbbb-0001-0001-0001-000000000001")


def _make_record(storage_key: str = "factory/event/file.jpg") -> EvidenceFileRecord:
    return EvidenceFileRecord(
        id=uuid4(),
        factory_id=FACTORY_ID,
        event_id=EVENT_ID,
        kind=EvidenceKind.SNAPSHOT,
        storage_key=storage_key,
        content_type="image/jpeg",
        size_bytes=1024,
        sha256="a" * 64,
        captured_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
    )


class TestEvidenceServiceFacade(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.svc = EvidenceService(storage_dir=Path(self.tmp))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_upload_delegates_to_upload_service(self):
        record = _make_record()
        req = EvidenceUploadRequest(
            factory_id=FACTORY_ID,
            event_id=EVENT_ID,
            captured_at=datetime.now(tz=timezone.utc),
        )
        conn = MagicMock()
        with patch.object(self.svc._upload_svc, "upload", return_value=record) as mock_upload:
            result = self.svc.upload(conn, req, b"bytes", "image/jpeg")
        mock_upload.assert_called_once_with(conn, req, b"bytes", "image/jpeg")
        self.assertEqual(result.id, record.id)

    def test_get_metadata_delegates(self):
        record = _make_record()
        meta = EvidenceMetadataResponse.from_record(record)
        conn = MagicMock()
        with patch.object(self.svc._retrieval_svc, "get_metadata", return_value=meta):
            result = self.svc.get_metadata(conn, record.id, FACTORY_ID)
        self.assertEqual(result.id, record.id)

    def test_list_by_event_delegates(self):
        conn = MagicMock()
        with patch.object(self.svc._retrieval_svc, "list_by_event", return_value=[]):
            result = self.svc.list_by_event(conn, EVENT_ID, FACTORY_ID)
        self.assertEqual(result, [])

    def test_list_by_incident_delegates(self):
        conn = MagicMock()
        with patch.object(self.svc._retrieval_svc, "list_by_incident", return_value=[]):
            result = self.svc.list_by_incident(conn, uuid4(), FACTORY_ID)
        self.assertEqual(result, [])

    def test_list_by_factory_delegates(self):
        resp = EvidenceListResponse(total=0, data=[])
        conn = MagicMock()
        with patch.object(self.svc._retrieval_svc, "list_by_factory", return_value=resp):
            result = self.svc.list_by_factory(conn, FACTORY_ID)
        self.assertEqual(result.total, 0)

    def test_download_delegates(self):
        record = _make_record()
        conn = MagicMock()
        with patch.object(
            self.svc._retrieval_svc, "download", return_value=(b"bytes", record)
        ):
            raw, ret = self.svc.download(conn, record.id, FACTORY_ID)
        self.assertEqual(raw, b"bytes")

    def test_verify_integrity_delegates(self):
        result = IntegrityVerificationResult(
            evidence_id=uuid4(),
            storage_key="key",
            stored_sha256=None,
            computed_sha256="c" * 64,
            integrity_ok=True,
            message="ok",
        )
        conn = MagicMock()
        with patch.object(self.svc._integrity_svc, "verify", return_value=result):
            ret = self.svc.verify_integrity(conn, result.evidence_id, FACTORY_ID)
        self.assertTrue(ret.integrity_ok)

    def test_get_evidence_service_singleton(self):
        """get_evidence_service() returns a singleton."""
        import incident_evidence.services.evidence_service as es_module
        es_module._instance = None  # reset
        s1 = es_module.get_evidence_service(storage_dir=Path(self.tmp))
        s2 = es_module.get_evidence_service(storage_dir=Path(self.tmp))
        self.assertIs(s1, s2)
        es_module._instance = None  # clean up


if __name__ == "__main__":
    unittest.main()
