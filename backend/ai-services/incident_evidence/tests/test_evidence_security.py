"""
incident_evidence/tests/test_evidence_security.py
Security and integration readiness tests for Phase 1.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from incident_evidence import config as ev_config
from incident_evidence.exceptions import EvidenceNotFoundError, StorageError
from incident_evidence.services.evidence_service import EvidenceService, get_evidence_service
from incident_evidence.storage.local_storage import LocalStorage


class TestEvidenceSecurityPhase1(unittest.TestCase):
    def test_no_hardcoded_db_credentials_in_config(self):
        self.assertFalse(hasattr(ev_config, "DATABASE_URL"))
        config_text = Path(ev_config.__file__).read_text(encoding="utf-8")
        self.assertNotIn("postgresql+", config_text.lower())
        self.assertNotIn("://", config_text.lower())
        self.assertNotIn("operix_db", config_text.lower())

    def test_no_engine_or_sessionmaker_in_module(self):
        module_root = Path(ev_config.__file__).parent
        for py_file in module_root.rglob("*.py"):
            if "tests" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8")
            self.assertNotIn("create_engine(", text, f"Found create_engine in {py_file}")
            self.assertNotIn("sessionmaker(", text, f"Found sessionmaker in {py_file}")

    def test_storage_key_format_enforces_factory_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            fid = uuid4()
            eid = uuid4()
            evid = uuid4()
            key = storage.generate_key(fid, eid, evid, ".jpg")
            self.assertTrue(key.startswith(f"f/{fid}/"))
            self.assertEqual(key, f"f/{fid}/{eid}/{evid}.jpg")

    def test_path_traversal_and_unsafe_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalStorage(Path(tmp))
            unsafe_keys = [
                "",
                "../secret.txt",
                "f/../../etc/passwd",
                "/etc/passwd",
                "\\windows\\system32",
                "f/abc/def\x00.jpg",
                "C:\\temp\\evil.jpg",
            ]
            for bad_key in unsafe_keys:
                with self.assertRaises(StorageError, msg=f"Failed to reject {bad_key!r}"):
                    storage.save(bad_key, b"data")
                with self.assertRaises(StorageError, msg=f"Failed to reject load {bad_key!r}"):
                    storage.load(bad_key)

    def test_get_evidence_service_respects_new_storage_dir(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            svc1 = get_evidence_service(storage_dir=Path(tmp1))
            self.assertEqual(svc1._storage._root, Path(tmp1).resolve())
            svc2 = get_evidence_service(storage_dir=Path(tmp2))
            self.assertEqual(svc2._storage._root, Path(tmp2).resolve())

    def test_cross_factory_retrieval_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = EvidenceService(storage_dir=Path(tmp))
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = None
            with self.assertRaises(EvidenceNotFoundError):
                svc.get_metadata(mock_conn, uuid4(), uuid4())
            with self.assertRaises(EvidenceNotFoundError):
                svc.download(mock_conn, uuid4(), uuid4())


if __name__ == "__main__":
    unittest.main()
