# Operix AI Services — Security, Hardening & Tenant Isolation Report

**Author:** Abdallah Waleed (AI & Analytical Services Lead)  
**Security Standard:** Enterprise Industrial Defense-in-Depth  
**Target Environment:** Operix Industrial AI Safety Platform  
**Status:** ✅ **VERIFIED & SECURED**

---

## 1. Multi-Tenant Factory Isolation

Operix is a multi-tenant platform serving multiple independent industrial factories. Cross-tenant data leakage represents a critical safety and compliance violation. Multi-tenant boundaries are strictly enforced across all four service layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway / Router                     │
│               (Validates factory_id from JWT)               │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐       ┌─────────────────┐
│  SQL Layer   │       │ Storage Disk │       │   Vector Store  │
│  factory_id  │       │ f/{factory}/ │       │   metadata flt  │
│   in WHERE   │       │  sandboxed   │       │  tenant scoped  │
└──────────────┘       └──────────────┘       └─────────────────┘
```

### 1.1 Database Multi-Tenant Isolation
- **Workforce Analytics:** Every single SQL query includes an explicit `WHERE factory_id = :factory_id` filter. No cross-factory aggregations or wildcards are executed.
- **Incident Evidence:** All queries into `evidence_files` join or filter by `factory_id`. When retrieving by `evidence_id`, the service verifies `stored_record.factory_id == requested_factory_id`. Any mismatch immediately triggers `FactoryMismatchError` (HTTP 403 Forbidden).
- **Composite Foreign Keys:** PostgreSQL enforces referential integrity on `(factory_id, event_id)`. An event from Factory A cannot have evidence linked to Factory B.

### 1.2 Storage Isolation
- Every evidence file path strictly begins with the factory prefix:
  `f/{factory_id}/{event_id}/{evidence_id}.{ext}`
- This satisfies PostgreSQL's check constraint `CHECK (storage_key ~~ ('f/' || factory_id || '/%'))`.
- Storage directory access cannot cross factory root boundaries.

### 1.3 Vector Store Tenant Scoping
- In `llm_rag_assistant`, indexed chunks carry `factory_id` in their metadata.
- When querying the vector store with a `factory_id` filter:
  * Only chunks matching that specific `factory_id` or designated global SOP manuals (`meta.factory_id is None`) are evaluated.
  * Proprietary safety documents of Factory A can never be retrieved by an operator querying Factory B.

---

## 2. Storage Hardening & Path Traversal Prevention

Unrestricted file uploads and path traversal (`../../etc/passwd`) are common attack vectors. The incident evidence module implements rigorous path sanitization:

### 2.1 Deterministic Key Generation
- The user/client **never** controls the storage filename, key, or path.
- The storage key is generated deterministically by the backend:
  ```python
  def generate_key(factory_id: UUID, event_id: UUID, evidence_id: UUID, ext: str) -> str:
      clean_ext = ext.lstrip(".").lower()
      return f"f/{factory_id}/{event_id}/{evidence_id}.{clean_ext}"
  ```
- All path elements (`factory_id`, `event_id`, `evidence_id`) are strongly typed Python `UUID` objects. String injections, directory traversal dots (`..`), null bytes (`%00`), and slashes are physically impossible.

### 2.2 Filesystem Sandboxing & Escape Prevention
In `LocalStorage`, every read, write, and stream operation resolves the absolute path and verifies that it resides strictly within the configured storage directory:

```python
def _resolve(self, storage_key: str) -> Path:
    # Normalize and reject path traversal attempts
    cleaned = Path(storage_key.replace("\\", "/")).as_posix().lstrip("/")
    target = (self.storage_dir / cleaned).resolve()
    if not target.is_relative_to(self.storage_dir.resolve()):
        raise SecurityError(f"Path traversal detected: {storage_key}")
    return target
```

---

## 3. Deep Content Validation & Magic Bytes Inspection

Relying solely on HTTP `Content-Type` headers or file extensions allows attackers to upload executable malware disguised as images.

### 3.1 Binary Magic Header Verification
`EvidenceUploadService` inspects the initial raw bytes of every incoming file before persisting it to disk:

| Supported Format | Required Magic Bytes Signature | Offset |
| :--- | :--- | :--- |
| **PNG** | `b"\x89PNG\r\n\x1a\n"` | Byte 0 |
| **JPEG / JPG** | `b"\xff\xd8\xff"` | Byte 0 |
| **WebP** | `b"RIFF"` followed by `b"WEBP"` | Bytes 0–4 & 8–12 |
| **MP4 / MOV** | `b"ftyp"` | Bytes 4–8 |
| **MKV / WebM** | `b"\x1a\x45\xdf\xa3"` (EBML header) | Byte 0 |
| **AVI** | `b"RIFF"` followed by `b"AVI "` | Bytes 0–4 & 8–12 |

If a file claims to be an image or video but fails magic signature matching, it is immediately rejected with `InvalidMimeTypeError`.

### 3.2 Enforcement of Size Quotas
- Maximum image snapshot size: **10 MB** (`MAX_IMAGE_SIZE_BYTES`)
- Maximum video clip size: **50 MB** (`MAX_VIDEO_SIZE_BYTES`)
- Minimum file size: **1 Byte** (Zero-byte uploads rejected per DB check constraint)

---

## 4. Cryptographic Chain of Custody (Forensic SHA-256)

For industrial incident investigations, evidence must be legally defensible and tamper-evident:

1. **Fingerprint at Ingestion:** Upon upload, the full binary stream is hashed via `hashlib.sha256()`. The resulting 64-character hexadecimal digest is recorded immutably in the PostgreSQL `evidence_files.sha256` column.
2. **On-Demand Forensic Audit:** The `EvidenceIntegrityService` provides an endpoint (`/api/v1/evidence/{id}/integrity`) that recalculates the SHA-256 hash of the stored file on disk and compares it to the database record.
3. **Detection of Bit Rot or Tampering:** If even a single bit of the file on disk is altered, `is_intact` returns `False`, raising a tamper alert.

---

## 5. Agentic Remediation RBAC & Idempotency Safeguards

The LLM RAG Assistant is capable of proposing agentic remediation actions (e.g. triggering maintenance tickets, escalating alerts, issuing emergency notifications). Automated execution presents real-world risks if left unconstrained:

### 5.1 Role-Based Privilege Boundaries
- **Operator Role:** Operators can query SOPs, retrieve answers, and view proposed actions. They **cannot** execute critical actions (escalations or broadcast alerts). The service rejects them with:
  ```json
  {
    "status": "rejected",
    "message": "Action 'escalation' rejected: requires supervisor or factory_manager privileges."
  }
  ```
- **Supervisor & Factory Manager Roles:** Permitted to execute confirmed remediation actions.

### 5.2 Idempotency Key Defense Against Replay Attacks
Network retries or double-clicking an "Approve Action" button could lead to duplicated maintenance dispatches or redundant notifications.
- The `OperixActionService` accepts an `idempotency_key` (UUID or client-generated token).
- Cached execution results are returned immediately for duplicate keys without re-executing downstream actions.

### 5.3 Durable Audit Logging Hook
`OperixActionService` provides an `audit_callback` parameter. When integrated with Seif's backend, every action execution event emits an immutable audit event containing:
- Timestamp (UTC)
- Executing user ID and confirmed role
- Factory ID
- Audit reference code (e.g. `AUDIT-20261122-C842B1`)
- Action parameters and payload
