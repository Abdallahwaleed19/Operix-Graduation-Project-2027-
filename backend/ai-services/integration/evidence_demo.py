"""
integration/evidence_demo.py
Offline demonstration of the Incident Evidence module.

Demonstrates:
  1. File upload flow with synthetic test image (no real DB needed).
  2. LocalStorage key generation and file retrieval.
  3. SHA-256 integrity verification.
  4. Retrieval service query patterns (mocked DB).

This script uses a temporary directory for all file storage
and mocks the DB connection — it does NOT modify the real database.

Usage (PowerShell from backend/ai-services/):
    $env:PYTHONPATH="."
    python integration/evidence_demo.py
"""
from __future__ import annotations

import hashlib
import struct
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

# ── Synthetic test image (1×1 red pixel PNG, no external files needed) ──────
def _make_test_png() -> bytes:
    """Generate a valid minimal 1×1 red-pixel PNG in memory."""
    def _chunk(name: bytes, data: bytes) -> bytes:
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"  # filter byte + R, G, B
    compressed = zlib.compress(raw)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def demo_local_storage(tmp_dir: Path) -> None:
    print("\n" + "─" * 60)
    print("  DEMO 1: LocalStorage key generation and file operations")
    print("─" * 60)

    from incident_evidence.storage.local_storage import LocalStorage
    storage = LocalStorage(tmp_dir)

    factory_id = UUID("aaaaaaaa-0001-0001-0001-000000000001")
    event_id = UUID("bbbbbbbb-0001-0001-0001-000000000001")
    evidence_id = uuid4()

    key = storage.generate_key(factory_id, event_id, evidence_id, ".png")
    print(f"  [+] Generated storage key: {key}")

    png_bytes = _make_test_png()
    written = storage.save(key, png_bytes)
    print(f"  [+] Saved {written} bytes to storage")

    assert storage.exists(key), "File should exist after save"
    loaded = storage.load(key)
    assert loaded == png_bytes, "Loaded bytes should match saved bytes"
    print(f"  [+] Loaded {len(loaded)} bytes — matches original ✓")

    size = storage.size(key)
    print(f"  [+] File size: {size} bytes")

    abs_path = storage.absolute_path(key)
    print(f"  [+] Absolute path: {abs_path}")

    # Stream in chunks
    chunks = list(storage.stream(key, chunk_size=16))
    total = sum(len(c) for c in chunks)
    assert total == len(png_bytes)
    print(f"  [+] Streamed in {len(chunks)} chunk(s), total {total} bytes ✓")


def demo_upload_service(tmp_dir: Path) -> str:
    """Returns the storage_key of the uploaded file for subsequent demos."""
    print("\n" + "─" * 60)
    print("  DEMO 2: EvidenceUploadService (mocked DB)")
    print("─" * 60)

    from incident_evidence.storage.local_storage import LocalStorage
    from incident_evidence.services.evidence_upload_service import EvidenceUploadService
    from incident_evidence.schemas import EvidenceUploadRequest, EvidenceKind

    storage = LocalStorage(tmp_dir)
    svc = EvidenceUploadService(storage=storage)

    factory_id = UUID("aaaaaaaa-0001-0001-0001-000000000001")
    event_id = UUID("bbbbbbbb-0001-0001-0001-000000000001")

    png_bytes = _make_test_png()
    expected_sha = hashlib.sha256(png_bytes).hexdigest()

    request = EvidenceUploadRequest(
        factory_id=factory_id,
        event_id=event_id,
        captured_at=datetime.now(tz=timezone.utc),
    )

    # Mock the DB repo
    captured = {}

    def mock_create_record(**kwargs):
        captured.update(kwargs)
        from incident_evidence.schemas import EvidenceFileRecord
        return EvidenceFileRecord(
            id=uuid4(),
            factory_id=factory_id,
            event_id=event_id,
            kind=EvidenceKind.IMAGE,
            storage_key=kwargs["storage_key"],
            content_type="image/png",
            size_bytes=kwargs["size_bytes"],
            sha256=kwargs["sha256"],
            captured_at=kwargs["captured_at"],
            created_at=datetime.now(tz=timezone.utc),
        )

    conn = MagicMock()
    from unittest.mock import patch
    with patch("incident_evidence.services.evidence_upload_service.EvidenceRepository") as MockRepo:
        MockRepo.return_value.create_record.side_effect = mock_create_record
        record = svc.upload(conn, request, png_bytes, "image/png")

    print(f"  [+] Upload succeeded!")
    print(f"      Evidence ID  : {record.id}")
    print(f"      Kind         : {record.kind.value}")
    print(f"      Storage key  : {record.storage_key}")
    print(f"      SHA-256      : {record.sha256[:16]}…")
    assert record.sha256 == expected_sha, "SHA-256 mismatch!"
    print(f"  [+] SHA-256 verified ✓")

    return record.storage_key


def demo_integrity_service(tmp_dir: Path, storage_key: str) -> None:
    print("\n" + "─" * 60)
    print("  DEMO 3: EvidenceIntegrityService verification")
    print("─" * 60)

    from incident_evidence.storage.local_storage import LocalStorage
    from incident_evidence.services.evidence_integrity_service import EvidenceIntegrityService
    from incident_evidence.schemas import EvidenceFileRecord, EvidenceKind

    storage = LocalStorage(tmp_dir)
    svc = EvidenceIntegrityService(storage=storage)

    # Read actual file from disk
    actual_bytes = storage.load(storage_key)
    actual_sha = hashlib.sha256(actual_bytes).hexdigest()

    record = EvidenceFileRecord(
        id=uuid4(),
        factory_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
        event_id=UUID("bbbbbbbb-0001-0001-0001-000000000001"),
        kind=EvidenceKind.IMAGE,
        storage_key=storage_key,
        content_type="image/png",
        size_bytes=len(actual_bytes),
        sha256=actual_sha,
        captured_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
    )

    conn = MagicMock()
    from unittest.mock import patch
    with patch("incident_evidence.services.evidence_integrity_service.EvidenceRepository") as MockRepo:
        MockRepo.return_value.get_by_id.return_value = record
        result = svc.verify(conn, record.id, record.factory_id)

    print(f"  [+] Stored SHA-256  : {result.stored_sha256[:16]}…")
    print(f"  [+] Computed SHA-256: {result.computed_sha256[:16]}…")
    print(f"  [+] Integrity OK    : {result.integrity_ok}")
    print(f"  [+] Message         : {result.message}")
    assert result.integrity_ok


def demo_schemas() -> None:
    print("\n" + "─" * 60)
    print("  DEMO 4: Pydantic schema validation")
    print("─" * 60)

    from incident_evidence.schemas import EvidenceKind, EvidenceUploadRequest
    from incident_evidence.api_contracts.requests import EvidenceUploadMetadata

    factory_id = UUID("aaaaaaaa-0001-0001-0001-000000000001")
    event_id = UUID("bbbbbbbb-0001-0001-0001-000000000001")

    meta = EvidenceUploadMetadata(factory_id=factory_id, event_id=event_id)
    req = meta.to_upload_request()
    print(f"  [+] EvidenceUploadMetadata → EvidenceUploadRequest ✓")
    print(f"      factory_id: {req.factory_id}")
    print(f"      event_id  : {req.event_id}")

    for kind in EvidenceKind:
        assert len(kind.value) <= 8, f"Kind value '{kind.value}' exceeds VARCHAR(8)"
    print(f"  [+] All EvidenceKind values fit VARCHAR(8) ✓")


def main() -> None:
    print("=" * 60)
    print("  Operix — Incident Evidence Module Demo")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        demo_local_storage(tmp_dir)
        storage_key = demo_upload_service(tmp_dir)
        demo_integrity_service(tmp_dir, storage_key)
        demo_schemas()

    print("\n" + "=" * 60)
    print("  ✅ All evidence demos passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
