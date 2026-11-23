"""
incident_evidence/tests/test_api_contracts.py
Tests for Pydantic request and response contracts of the evidence module.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from incident_evidence.api_contracts.requests import (
    EvidenceUploadMetadata,
    IncidentEvidenceQueryParams,
)
from incident_evidence.api_contracts.responses import (
    EvidenceDownloadInfo,
    EvidenceErrorResponse,
    EvidenceSingleResponse,
    IntegrityVerificationResponse,
)
from incident_evidence.schemas import (
    EvidenceKind,
    EvidenceListResponse,
    EvidenceMetadataResponse,
    EvidenceUploadRequest,
    EvidenceUploadResponse,
    IntegrityVerificationResult,
)

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")
EVENT_ID = UUID("bbbbbbbb-0001-0001-0001-000000000001")
EVIDENCE_ID = UUID("cccccccc-0003-0003-0003-000000000003")


def _make_meta() -> EvidenceMetadataResponse:
    return EvidenceMetadataResponse(
        id=EVIDENCE_ID,
        factory_id=FACTORY_ID,
        event_id=EVENT_ID,
        kind=EvidenceKind.SNAPSHOT,
        storage_key="f/aaaa/bbbb/cccc.jpg",
        content_type="image/jpeg",
        size_bytes=10240,
        sha256="a" * 64,
        captured_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
        is_expired=False,
        is_purged=False,
    )


class TestEvidenceUploadMetadata(unittest.TestCase):

    def test_minimal(self):
        m = EvidenceUploadMetadata(factory_id=FACTORY_ID, event_id=EVENT_ID)
        self.assertEqual(m.factory_id, FACTORY_ID)
        self.assertIsNone(m.duration_s)

    def test_to_upload_request(self):
        m = EvidenceUploadMetadata(factory_id=FACTORY_ID, event_id=EVENT_ID)
        req = m.to_upload_request()
        self.assertIsInstance(req, EvidenceUploadRequest)
        self.assertEqual(req.factory_id, FACTORY_ID)

    def test_with_duration(self):
        m = EvidenceUploadMetadata(factory_id=FACTORY_ID, event_id=EVENT_ID, duration_s=30.5)
        self.assertAlmostEqual(m.duration_s, 30.5)

    def test_missing_factory_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            EvidenceUploadMetadata(event_id=EVENT_ID)


class TestIncidentEvidenceQueryParams(unittest.TestCase):

    def test_required_factory(self):
        params = IncidentEvidenceQueryParams(factory_id=FACTORY_ID)
        self.assertEqual(params.factory_id, FACTORY_ID)
        self.assertIsNone(params.kind)

    def test_with_kind(self):
        params = IncidentEvidenceQueryParams(
            factory_id=FACTORY_ID, kind=EvidenceKind.CLIP
        )
        self.assertEqual(params.kind, EvidenceKind.CLIP)

    def test_missing_factory_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            IncidentEvidenceQueryParams()


class TestEvidenceSingleResponse(unittest.TestCase):

    def test_construction(self):
        resp = EvidenceSingleResponse(data=_make_meta())
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.kind, EvidenceKind.SNAPSHOT)

    def test_json_roundtrip(self):
        resp = EvidenceSingleResponse(data=_make_meta())
        raw = resp.model_dump_json()
        restored = EvidenceSingleResponse.model_validate_json(raw)
        self.assertEqual(restored.data.id, EVIDENCE_ID)


class TestEvidenceListResponse(unittest.TestCase):

    def test_empty(self):
        resp = EvidenceListResponse(total=0, data=[])
        self.assertEqual(resp.total, 0)
        self.assertTrue(resp.success)

    def test_with_items(self):
        resp = EvidenceListResponse(total=1, data=[_make_meta()])
        self.assertEqual(len(resp.data), 1)


class TestEvidenceUploadResponse(unittest.TestCase):

    def test_construction(self):
        resp = EvidenceUploadResponse(data=_make_meta())
        self.assertTrue(resp.success)
        self.assertIn("successfully", resp.message)


class TestIntegrityVerificationResult(unittest.TestCase):

    def test_ok(self):
        result = IntegrityVerificationResult(
            evidence_id=EVIDENCE_ID,
            storage_key="aaaa/bbbb/cccc.jpg",
            stored_sha256="a" * 64,
            computed_sha256="a" * 64,
            integrity_ok=True,
            message="SHA-256 matches.",
        )
        self.assertTrue(result.integrity_ok)

    def test_mismatch(self):
        result = IntegrityVerificationResult(
            evidence_id=EVIDENCE_ID,
            storage_key="aaaa/bbbb/cccc.jpg",
            stored_sha256="a" * 64,
            computed_sha256="b" * 64,
            integrity_ok=False,
            message="INTEGRITY FAILURE.",
        )
        self.assertFalse(result.integrity_ok)


class TestIntegrityVerificationResponse(unittest.TestCase):

    def test_construction(self):
        result = IntegrityVerificationResult(
            evidence_id=EVIDENCE_ID,
            storage_key="key",
            stored_sha256=None,
            computed_sha256="c" * 64,
            integrity_ok=True,
            message="No stored hash.",
        )
        resp = IntegrityVerificationResponse(data=result)
        self.assertTrue(resp.success)


class TestEvidenceDownloadInfo(unittest.TestCase):

    def test_construction(self):
        info = EvidenceDownloadInfo(
            evidence_id=EVIDENCE_ID,
            storage_key="key.jpg",
            file_path="/storage/evidence/key.jpg",
            mime_type="image/jpeg",
            size_bytes=10240,
            suggested_filename="evidence_cccc.jpg",
        )
        self.assertEqual(info.mime_type, "image/jpeg")


class TestEvidenceErrorResponse(unittest.TestCase):

    def test_construction(self):
        err = EvidenceErrorResponse(
            error_code="EVIDENCE_NOT_FOUND",
            message="Not found.",
        )
        self.assertFalse(err.success)
        self.assertIsNone(err.detail)


if __name__ == "__main__":
    unittest.main()
