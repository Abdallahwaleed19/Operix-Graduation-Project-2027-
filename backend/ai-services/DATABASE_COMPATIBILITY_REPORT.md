# Operix AI Services — PostgreSQL 18 Database Compatibility Report

**Database System:** PostgreSQL 18 (x86_64-pc-windows-msvc)  
**Database Name:** `operix_db`  
**Database Maintainer:** Muhammad Salah  
**AI Services Maintainer:** Abdallah Waleed  
**Audit Date:** November 2026  
**Status:** ✅ **100% STRICTLY COMPATIBLE (ZERO SCHEMA MODIFICATIONS REQUIRED)**

---

## 1. Executive Summary & Verification Methodology

A comprehensive, live read-only inspection was performed against the authoritative PostgreSQL 18 database `operix_db`. All 22 relational tables, custom PostgreSQL enums, foreign key hierarchies, composite keys, check constraints, and index definitions were queried using `information_schema` and `pg_catalog`.

The application code across all four AI service modules (`workforce_analytics`, `llm_rag_assistant`, `reports_generation`, `incident_evidence`) has been synchronized to adhere strictly to the database schema. **No tables, columns, constraints, or enums were created or modified in PostgreSQL.**

---

## 2. PostgreSQL 18 Catalog & Live Table Registry

The authoritative database contains 22 tables:

1. `alert_deliveries`
2. `alerts`
3. `auth_tokens`
4. `cameras`
5. `departments`
6. `events`
7. `evidence_files`
8. `factories`
9. `factory_memberships`
10. `incidents`
11. `monitoring_zones`
12. `notification_targets`
13. `permissions`
14. `role_permissions`
15. `roles`
16. `safety_rules`
17. `sensor_readings`
18. `sensors`
19. `unobserved_gaps`
20. `users`
21. `alembic_version`
22. `spatial_ref_sys`

---

## 3. Deep Dive: `evidence_files` Table & Schema Rules

The `evidence_files` table stores forensic media linked to industrial safety events.

### 3.1 Column Specifications & Live Data Types

| Column Name | PostgreSQL Type | Nullable | Default / Generation | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary Key |
| `factory_id` | `uuid` | NO | — | Factory tenant foreign key |
| `event_id` | `uuid` | NO | — | Composite FK with `factory_id` into `events` |
| `kind` | `USER-DEFINED` (`evidence_kind`) | NO | — | Native PostgreSQL Enum |
| `storage_key` | `text` | NO | — | Relative path on object/local storage |
| `content_type` | `text` | NO | — | Standard MIME type |
| `size_bytes` | `bigint` | NO | — | Stored payload size in bytes |
| `sha256` | `character varying(64)` | NO | — | Hex-encoded cryptographic SHA-256 hash |
| `duration_s` | `integer` | YES | `NULL` | Video clip length (mandatory if clip) |
| `captured_at` | `timestamp with time zone` | NO | `now()` | Physical timestamp of event detection |
| `expires_at` | `timestamp with time zone` | YES | `NULL` | Data retention policy cutoff |
| `purged_at` | `timestamp with time zone` | YES | `NULL` | Timestamp when physical file was wiped |
| `created_at` | `timestamp with time zone` | NO | `now()` | Database insertion timestamp |

### 3.2 Native Enum: `evidence_kind`
Querying `pg_type` and `pg_enum` reveals the exact allowed values:
```sql
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'evidence_kind'::regtype;
-- Results:
-- 1. 'snapshot'
-- 2. 'clip'
```
> **Application Adjustment:**
> Previously, the Python code defined `EvidenceKind.AUDIO = "audio"`. Because `'audio'` does NOT exist in PostgreSQL's `evidence_kind` enum, any audio insertion crashed with `psycopg2.errors.InvalidTextRepresentation`.
> **Resolution:** `incident_evidence` was updated to remove `audio`. Any upload with audio MIME types (e.g. `audio/wav`, `audio/mpeg`) is rejected immediately at the Pydantic/Service boundary with `InvalidMimeTypeError`.

### 3.3 Check Constraints Audit

1. **`evidence_files_check`:**
   ```sql
   CHECK (kind = 'snapshot'::evidence_kind OR duration_s IS NOT NULL)
   ```
   *Implication:* If `kind = 'clip'`, `duration_s` cannot be null.  
   *Application Enforcement:* `EvidenceUploadService.upload()` mandates `duration_s > 0` for all video uploads before attempting DB write.

2. **`evidence_files_check1`:**
   ```sql
   CHECK (storage_key ~~ (('f/'::text || (factory_id)::text) || '/%'::text))
   ```
   *Implication:* Every storage key must begin with `f/{factory_id}/`.  
   *Application Enforcement:* `LocalStorage.generate_key()` was updated to produce `f/{factory_id}/{event_id}/{evidence_id}{ext}`.

3. **`evidence_files_size_bytes_check`:**
   ```sql
   CHECK (size_bytes > 0)
   ```
   *Implication:* Zero-byte or empty files are strictly rejected by the database.  
   *Application Enforcement:* `EvidenceUploadService` raises `FileSizeLimitExceededError("Evidence file is empty (0 bytes).")` if `len(file_bytes) == 0`.

### 3.4 Foreign Key Chains & Multi-Tenant Referential Integrity
- `evidence_files.(factory_id, event_id)` $\rightarrow$ `events.(factory_id, id)` ON DELETE CASCADE
- `events.(factory_id, incident_id)` $\rightarrow$ `incidents.(factory_id, id)`
- `events.(factory_id, camera_id)` $\rightarrow$ `cameras.(factory_id, id)`

Because the foreign key on `evidence_files` references both `factory_id` AND `event_id`, it is impossible to insert an evidence file under a factory ID that does not match the parent event's factory ID.

---

## 4. Analytical & Reporting Tables Audit

### 4.1 `safety_rules` Table
Inspection of live columns:
```
['id', 'factory_id', 'department_id', 'zone_id', 'sensor_id', 'name', 'event_type', 'severity', 'min_confidence', 'min_duration_s', 'threshold_value', 'notify', 'is_enabled', 'version', 'created_at', 'updated_at']
```
- **Discrepancy Detected:** Reports generation code originally queried `is_active = true`.
- **Live Database Reality:** The column name is `is_enabled` (`boolean`).
- **Resolution:** SQL query in `reports_generation/repositories.py` line 83 updated to:
  ```sql
  SELECT count(*) FROM safety_rules WHERE factory_id = :factory_id AND is_enabled = true
  ```

### 4.2 `unobserved_gaps` Table
Inspection of live columns:
```
['id', 'factory_id', 'camera_id', 'started_at', 'ended_at', 'reason', 'created_at']
```
- **Discrepancy Detected:** Reports generation code queried `severity` and `resolved_at`.
- **Live Database Reality:** `unobserved_gaps` has no `severity` or `resolved_at` columns; downtime periods are defined by `started_at` and `ended_at`.
- **Resolution:** `reports_generation/repositories.py` line 62 updated to select only valid columns.

### 4.3 `incidents` Table
Inspection of live columns:
```
['id', 'factory_id', 'incident_type', 'severity', 'state', 'opened_at', 'last_event_at', 'reviewed_by', 'reviewed_at', 'resolved_by', 'resolved_at', 'resolution_note', 'updated_at']
```
- **Validation:** Matches SQLAlchemy models and Pydantic schemas in `workforce_analytics` and `reports_generation` completely.

---

## 5. Non-Destructive Operation & Read-Only Guarantees

| Module | SQL Operation Types | Modifies Database? |
| :--- | :--- | :--- |
| `workforce_analytics` | `SELECT` queries, CTE aggregations | ❌ **Strictly Read-Only** |
| `reports_generation` | `SELECT` queries, counts, joins | ❌ **Strictly Read-Only** |
| `llm_rag_assistant` | `SELECT` (during DB knowledge ingestion) | ❌ **Strictly Read-Only** |
| `incident_evidence` | `SELECT`, `INSERT` into `evidence_files` | ✅ Controlled write to `evidence_files` only |

### Transactional Rollback Protection in `incident_evidence`
When an evidence file is uploaded:
1. Physical file is written to storage disk (`f/{factory_id}/...`).
2. An INSERT transaction is attempted on `evidence_files`.
3. If PostgreSQL raises any constraint violation or error, the session is rolled back (`session.rollback()`) and the saved file on disk is immediately deleted (`storage.delete(storage_key)`).
4. No orphaned records or orphaned disk files can occur.
