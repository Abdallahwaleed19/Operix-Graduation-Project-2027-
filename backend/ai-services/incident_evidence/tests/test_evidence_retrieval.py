"""
incident_evidence/tests/test_evidence_retrieval.py
Unit tests for EvidenceRetrievalService.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from incident_evidence.exceptions import EvidencePurgedError, EvidenceExpiredError
from incident_evidence.schemas import (
    EvidenceFileRecord,
    EvidenceKind,
    EvidenceListResponse,
    EvidenceMetadataResponse,
)
from incident_evidence.services.evidence_retrieval_service import EvidenceRetrievalService
from incident_evidence.storage.local_storage import LocalStorage

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
EVENT_ID = UUID("bbbbbbbb-0001-0001-0001-000000000001")
INCIDENT_ID = UUID("dddddddd-0001-0001-0001-000000000001")


def _make_record(
    purged: bool = False,
    expired: bool = False,
    kind: EvidenceKind = EvidenceKind.SNAPSHOT,
) -> EvidenceFileRecord:
    from datetime import timedelta
    return EvidenceFileRecord(
        id=uuid4(),
        factory_id=FACTORY_ID,
        event_id=EVENT_ID,
        kind=kind,
        storage_key="factory/event/file.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        sha256="a" * 64,
        captured_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
        purged_at=datetime.now(tz=timezone.utc) if purged else None,
        expires_at=(
            datetime(2000, 1, 1, tzinfo=timezone.utc) if expired else None
        ),
    )


class TestEvidenceRetrievalService(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = LocalStorage(Path(self.tmp))
        self.svc = EvidenceRetrievalService(storage=self.storage)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # get_metadata
    # ------------------------------------------------------------------

    def test_get_metadata_ok(self):
        record = _make_record()
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            meta = self.svc.get_metadata(conn, record.id, FACTORY_ID)
        self.assertIsInstance(meta, EvidenceMetadataResponse)
        self.assertEqual(meta.id, record.id)

    # ------------------------------------------------------------------
    # list_by_event
    # ------------------------------------------------------------------

    def test_list_by_event_empty(self):
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_event_id.return_value = []
            results = self.svc.list_by_event(conn, EVENT_ID, FACTORY_ID)
        self.assertEqual(results, [])

    def test_list_by_event_returns_items(self):
        records = [_make_record() for _ in range(3)]
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_event_id.return_value = records
            results = self.svc.list_by_event(conn, EVENT_ID, FACTORY_ID)
        self.assertEqual(len(results), 3)

    # ------------------------------------------------------------------
    # list_by_incident
    # ------------------------------------------------------------------

    def test_list_by_incident_returns_items(self):
        records = [_make_record(), _make_record(kind=EvidenceKind.CLIP)]
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_incident_id.return_value = records
            results = self.svc.list_by_incident(conn, INCIDENT_ID, FACTORY_ID)
        self.assertEqual(len(results), 2)

    # ------------------------------------------------------------------
    # list_by_factory
    # ------------------------------------------------------------------

    def test_list_by_factory_paginated(self):
        records = [_make_record() for _ in range(5)]
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.list_by_factory.return_value = (records, 10)
            resp = self.svc.list_by_factory(conn, FACTORY_ID, page=1, page_size=5)
        self.assertIsInstance(resp, EvidenceListResponse)
        self.assertEqual(resp.total, 10)
        self.assertEqual(len(resp.data), 5)

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------

    def test_download_purged_raises(self):
        record = _make_record(purged=True)
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            with self.assertRaises(EvidencePurgedError):
                self.svc.download(conn, record.id, FACTORY_ID)

    def test_download_expired_raises(self):
        record = _make_record(expired=True)
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            with self.assertRaises(EvidenceExpiredError):
                self.svc.download(conn, record.id, FACTORY_ID)

    def test_download_ok(self):
        record = _make_record()
        # Write the file to disk
        self.storage.save(record.storage_key, b"binary_content")
        conn = MagicMock()
        with patch(
            "incident_evidence.services.evidence_retrieval_service.EvidenceRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = record
            raw, ret_record = self.svc.download(conn, record.id, FACTORY_ID)
        self.assertEqual(raw, b"binary_content")
        self.assertEqual(ret_record.id, record.id)


if __name__ == "__main__":
    unittest.main()
