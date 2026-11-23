# Incident Evidence Module

**Module:** `incident_evidence/`  
**Task:** 4 — Incident Evidence Recording & Retrieval  
**Owner:** Abdallah Waleed (AI & Analytics Lead)  
**Status:** ✅ Complete — 46 tests passing

---

## Purpose

Provides validated upload, secure local storage, retrieval, and SHA-256 integrity verification for incident evidence files (images, videos, audio). Integrates with the existing `evidence_files` database table using its verified composite foreign-key relationships.

---

## Architecture

```
incident_evidence/
├── config.py                     ← DATABASE_URL, storage dir, file limits, MIME types
├── exceptions.py                 ← EvidenceBaseException hierarchy
├── schemas.py                    ← EvidenceKind, EvidenceFileRecord, all request/response models
├── repositories.py               ← EvidenceRepository (SELECT + INSERT on evidence_files)
├── storage/
│   ├── base_storage.py           ← BaseStorage abstract interface
│   └── local_storage.py          ← LocalStorage: UUID-keyed, path-traversal-safe filesystem backend
├── services/
│   ├── evidence_upload_service.py   ← Validation, SHA-256, atomic save + DB insert, rollback
│   ├── evidence_integrity_service.py← SHA-256 re-computation and comparison
│   ├── evidence_retrieval_service.py← Read access by ID, event, incident, factory
│   └── evidence_service.py          ← EvidenceService facade + get_evidence_service() singleton
├── api_contracts/
│   ├── requests.py               ← EvidenceUploadMetadata, IncidentEvidenceQueryParams
│   └── responses.py              ← All response envelopes
└── tests/                        ← 46 unit tests (no real DB, tempdir only)
```

---

## Database Relationship (Verified)

```
incidents.id
    ↑  (FK: events.incident_id — nullable)
events.id + events.factory_id
    ↑  (composite FK: evidence_files.(factory_id, event_id))
evidence_files
```

**To fetch evidence for an incident:**
```sql
SELECT ef.*
FROM evidence_files ef
JOIN events e ON ef.factory_id = e.factory_id AND ef.event_id = e.id
WHERE e.incident_id = :incident_id
  AND ef.factory_id = :factory_id
```

---

## Evidence Kinds (VARCHAR 8)

| Kind | MIME Types |
|---|---|
| `image` | `image/jpeg`, `image/png`, `image/webp`, `image/gif` |
| `video` | `video/mp4`, `video/mpeg`, `video/webm`, `video/quicktime`, `video/x-msvideo` |
| `audio` | `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/webm` |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | from `.env` | PostgreSQL connection string |
| `DEFAULT_FACTORY_ID` | `aaaaaaaa-0001-0001-0001-000000000001` | Default factory scope |
| `EVIDENCE_STORAGE_DIR` | `storage/evidence/` | Root for uploaded files |
| `MAX_EVIDENCE_SIZE_MB` | `100` | Maximum file size per upload |

---

## Storage Key Format

```
{factory_id}/{event_id}/{evidence_id}.{ext}
```

Example:
```
aaaaaaaa-0001-0001-0001-000000000001/
  bbbbbbbb-0001-0001-0001-000000000001/
    cccccccc-1234-5678-9abc-def012345678.jpg
```

---

## Usage

```python
from sqlalchemy import create_engine
from incident_evidence.services.evidence_service import get_evidence_service
from incident_evidence.schemas import EvidenceUploadRequest
from uuid import UUID
from datetime import datetime, timezone

engine = create_engine("postgresql+psycopg2://postgres:abdallah@localhost:5432/operix_db")
svc = get_evidence_service()

# Upload
with engine.connect() as conn:
    with conn.begin():
        request = EvidenceUploadRequest(
            factory_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
            event_id=UUID("bbbbbbbb-0001-0001-0001-000000000001"),
            captured_at=datetime.now(tz=timezone.utc),
        )
        with open("photo.jpg", "rb") as f:
            file_bytes = f.read()
        record = svc.upload(conn, request, file_bytes, "image/jpeg")
        print(f"Uploaded: {record.id} → {record.storage_key}")

# Verify integrity
with engine.connect() as conn:
    result = svc.verify_integrity(conn, record.id, record.factory_id)
    print(f"Integrity OK: {result.integrity_ok}")
    print(f"Message: {result.message}")

# List by incident
with engine.connect() as conn:
    evidence_list = svc.list_by_incident(
        conn,
        incident_id=UUID("dddddddd-0001-0001-0001-000000000001"),
        factory_id=UUID("aaaaaaaa-0001-0001-0001-000000000001"),
    )
    print(f"Found {len(evidence_list)} evidence files for incident")
```

---

## API Contracts (for Seif — FastAPI Integration)

### POST `/api/v1/evidence` — Upload Evidence
```python
from incident_evidence.api_contracts.requests import EvidenceUploadMetadata
from incident_evidence.api_contracts.responses import EvidenceUploadResponse

# Seif receives multipart/form-data with:
#   - metadata fields (factory_id, event_id, captured_at, duration_s, expires_at)
#   - file: UploadFile

meta = EvidenceUploadMetadata(factory_id=..., event_id=...)
request = meta.to_upload_request()
file_bytes = await file.read()
content_type = file.content_type

record = svc.upload(conn, request, file_bytes, content_type)
return EvidenceUploadResponse(data=EvidenceMetadataResponse.from_record(record))
```

### GET `/api/v1/evidence/{id}` — Get Metadata
```python
from incident_evidence.api_contracts.responses import EvidenceSingleResponse
meta = svc.get_metadata(conn, evidence_id=uuid, factory_id=uuid)
return EvidenceSingleResponse(data=meta)
```

### GET `/api/v1/evidence/{id}/download` — Download File
```python
# Returns FileResponse — Seif builds it using:
abs_path = svc._retrieval_svc.get_absolute_path(conn, evidence_id, factory_id)
# return FileResponse(path=str(abs_path), media_type=record.content_type)
```

### GET `/api/v1/incidents/{incident_id}/evidence` — Evidence for Incident
```python
from incident_evidence.api_contracts.requests import IncidentEvidenceQueryParams
records = svc.list_by_incident(conn, incident_id=uuid, factory_id=uuid)
```

### GET `/api/v1/evidence/{id}/verify` — Integrity Check
```python
from incident_evidence.api_contracts.responses import IntegrityVerificationResponse
result = svc.verify_integrity(conn, evidence_id=uuid, factory_id=uuid)
return IntegrityVerificationResponse(data=result)
```

---

## Taqi — Frontend Integration Examples

```typescript
// Upload evidence for an incident event
const formData = new FormData();
formData.append('factory_id', 'aaaaaaaa-0001-0001-0001-000000000001');
formData.append('event_id', 'bbbbbbbb-0001-0001-0001-000000000001');
formData.append('file', photoFile);

const response = await fetch('/api/v1/evidence', {
  method: 'POST',
  body: formData,
});
const { data } = await response.json();
// data.id → evidence ID for future reference
// data.sha256 → integrity hash

// Verify integrity of stored evidence
const verifyResponse = await fetch(`/api/v1/evidence/${data.id}/verify`);
const { data: verification } = await verifyResponse.json();
console.log('Integrity OK:', verification.integrity_ok);

// List all evidence for an incident
const listResponse = await fetch(
  `/api/v1/incidents/${incidentId}/evidence?factory_id=aaaa...&kind=image`
);
const { data: evidenceList } = await listResponse.json();
```

---

## Security Notes

- **Path traversal prevention**: `LocalStorage._safe_resolve()` verifies that every resolved path stays under the storage root.
- **UUID-based filenames**: No user-supplied filenames are used on disk.
- **Atomic writes**: Files are written to a temp path then atomically renamed; partial writes never become visible.
- **DB rollback on storage failure**: If the DB INSERT fails, the already-saved file is deleted.
- **Storage directory in `.gitignore`**: Evidence files are never committed to git.
- **Factory-scoped queries**: All DB queries include `factory_id` as a security boundary.

---

## Running Tests

```powershell
# From backend/ai-services/  (no real DB needed)
$env:PYTHONPATH="."
C:\Users\AbdallahWaleed\AppData\Local\Programs\Python\Python314\python.exe -m unittest discover -s incident_evidence/tests -p "test_*.py" -v
```

## Running the Demo

```powershell
# Fully offline — uses synthetic PNG and mocked DB
$env:PYTHONPATH="."
C:\Users\AbdallahWaleed\AppData\Local\Programs\Python\Python314\python.exe integration/evidence_demo.py
```
