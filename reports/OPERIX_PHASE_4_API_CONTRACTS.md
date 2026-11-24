# OPERIX — PHASE 4 API CONTRACTS
## REST API Specification for AI & Analytics Endpoints

**Target Audience:** Frontend Team (Toka), AI Team (Abdullah), Backend Engineers  
**Base Path:** `/api/v1`  
**Standard Envelope:** All successful endpoints return standard `APIResponse[T]` with `APIResponseMeta`.  
**Error Envelope:** All 4xx/5xx responses return `APIErrorResponse`.  

---

## 1. Authentication & Tenant Headers

| Header | Format | Required | Description |
|--------|--------|----------|-------------|
| `Authorization` | `Bearer <JWT>` | Required for human user context | Standard HS256 signed human JWT. |
| `X-Factory-Id` | UUID string | Optional (defaults to configured factory) | Enforces tenant scope for multi-factory isolation. |

---

## 2. Workforce Analytics Endpoints

### 1. `GET /api/v1/analytics/overview`
- **Summary:** Workforce Overview Metrics
- **Auth:** Standard Tenant Scope
- **Response Data:**
```json
{
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "total_users": 10,
  "active_workers": 8,
  "inactive_workers": 2,
  "invited_users": 0,
  "disabled_users": 0,
  "by_role": {
    "factory_admin": 1,
    "factory_manager": 2,
    "safety_supervisor": 5
  },
  "workers_by_department": "NOT AVAILABLE"
}
```

### 2. `GET /api/v1/analytics/attendance`
- **Summary:** Attendance & Activity Metrics
- **Query Parameters:**
  - `start_date` (ISO 8601 DateTime, optional)
  - `end_date` (ISO 8601 DateTime, optional)
- **Response Data:**
```json
{
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "active_workers": 8,
  "recorded_activities": 45
}
```

### 3. `GET /api/v1/analytics/incidents`
- **Summary:** Safety Incident Analytics
- **Query Parameters:** `start_date`, `end_date`
- **Response Data:**
```json
{
  "total_incidents": 15,
  "resolved_count": 12,
  "resolution_rate": 80.0,
  "by_type": { "ppe_violation": 10, "fall": 3, "fire": 2 },
  "by_severity": { "low": 5, "medium": 7, "high": 3, "critical": 0 }
}
```

### 4. `GET /api/v1/analytics/productivity`
- **Summary:** Worker Incident Handling Productivity
- **Query Parameters:** `start_date`, `end_date`, `low_threshold`, `high_threshold`
- **Response Data:**
```json
{
  "workers_evaluated": 8,
  "high_performers": 5,
  "low_performers": 1,
  "performance_breakdown": [
    {
      "user_id": "11111111-0001-0001-0001-000000000001",
      "full_name": "Supervisor Alpha",
      "role": "safety_supervisor",
      "incidents_reviewed": 8,
      "incidents_resolved": 7,
      "productivity_label": "high"
    }
  ]
}
```

### 5. `GET /api/v1/analytics/camera-coverage`
- **Summary:** Camera Coverage & Downtime Analysis
- **Query Parameters:** `period_hours` (float, default 720.0)
- **Response Data:**
```json
{
  "coverage_percentage": 98.5,
  "total_cameras": 10,
  "active_cameras": 10,
  "total_gaps": 3
}
```

### 6. `GET /api/v1/analytics/summary`
- **Summary:** Unified Dashboard Analytics Summary
- **Query Parameters:** `start_date`, `end_date`, `period_hours`
- **Response Data:** Consolidates overview, attendance, incidents, and camera metrics.

---

## 3. LLM RAG Assistant Endpoints

### 1. `POST /api/v1/assistant/ask`
- **Summary:** Grounded Question Answering with Safety Knowledge
- **Request Body:**
```json
{
  "question": "What is the mandatory PPE protocol for Zone C?",
  "conversation_id": "conv-user-12345",
  "language_preference": "auto"
}
```
- **Response Data:**
```json
{
  "answer": "All workers entering Zone C must wear safety helmets and high-visibility vests.",
  "conversation_id": "conv-user-12345",
  "has_sufficient_evidence": true,
  "citations": [
    {
      "source_title": "Factory Safety Manual Rev 4",
      "source_type": "manual_pdf",
      "source_id": "doc-04",
      "snippet": "Zone C requires hard hat and reflective vest."
    }
  ],
  "suggested_actions": [
    {
      "action_id": "act-prop-01",
      "action_type": "dispatch",
      "title": "Dispatch Safety Supervisor",
      "description": "Dispatch supervisor to inspect Zone C PPE compliance",
      "severity": "medium",
      "parameters": { "zone_name": "Zone C", "task": "ppe_audit" },
      "requires_confirmation": true
    }
  ],
  "provider": "ollama",
  "model_name": "qwen2.5-7b",
  "language": "en",
  "processing_time_seconds": 0.45
}
```

### 2. `POST /api/v1/assistant/actions/execute`
- **Summary:** Execute an Approved Remediation Action
- **Request Body:**
```json
{
  "action_id": "act-prop-01",
  "action_type": "create_incident",
  "parameters": {
    "incident_type": "ppe_violation",
    "severity": "high",
    "description": "Worker missing hard hat in Zone C"
  },
  "idempotency_key": "idemp-action-98765",
  "confirmed_by": "Supervisor Tarek"
}
```
- **Response Data:**
```json
{
  "action_id": "act-prop-01",
  "status": "executed",
  "message": "Incident created successfully [ID: 3fa85f64-5717-4562-b3fc-2c963f66afa6].",
  "audit_reference": "AUDIT-20261124-E8B1A2",
  "details": {
    "incident_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "incident_type": "ppe_violation",
    "severity": "high",
    "state": "detected"
  },
  "execution_timestamp": "2026-11-24T02:24:00Z"
}
```
*Note: Automatically emits real-time WebSocket events to factory subscribers (`incident_created`, `ai_action_completed`).*

### 3. `GET /api/v1/assistant/sources?q={query}`
- **Summary:** Retrieve Knowledge Citations Directly
- **Response Data:** List of `SourceCitation` objects matching the query.

### 4. `DELETE /api/v1/assistant/conversations/{conversation_id}`
- **Summary:** Clear Conversation History
- **Response Data:** `{"conversation_id": "conv-user-12345", "cleared": true}`

### 5. `GET /api/v1/assistant/health`
- **Summary:** Diagnostic Status of Vector Store and LLM Provider

---

## 4. Reports Generation Endpoints

### 1. `POST /api/v1/reports/generate`
- **Summary:** Request Generation of PDF/Excel Report
- **Request Body:**
```json
{
  "report_type": "comprehensive_safety",
  "format": "pdf",
  "date_from": "2026-11-01",
  "date_to": "2026-11-24"
}
```
- **Response Data (HTTP 201 Created):**
```json
{
  "report_id": "REP-20261124-7F8A1B",
  "report_type": "comprehensive_safety",
  "format": "pdf",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "title": "Comprehensive Safety Report",
  "file_name": "comprehensive_safety_REP-20261124-7F8A1B.pdf",
  "file_size_bytes": 45280,
  "mime_type": "application/pdf",
  "generated_at": "2026-11-24T02:24:00Z"
}
```

### 2. `GET /api/v1/reports`
- **Summary:** List Generated Reports for Tenant
- **Response Data:** Array of `ReportMetadata` objects.

### 3. `GET /api/v1/reports/{report_id}`
- **Summary:** Retrieve Report Metadata by ID
- **Security:** Rejects requests from other factories with HTTP 403 `TenantAccessDeniedException`.

### 4. `GET /api/v1/reports/{report_id}/download`
- **Summary:** Download Generated Artifact
- **Response:** Raw binary streaming response with `Content-Type: application/pdf` or `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- **Security:** Verified against path traversal; must reside in `REPORTS_STORAGE_DIR`.

---

## 5. Incident Evidence Endpoints

### 1. `POST /api/v1/evidence/upload`
- **Summary:** Upload Evidence Snapshot or Video Clip
- **Request Body (JSON Base64):**
```json
{
  "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "kind": "snapshot",
  "file_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "content_type": "image/png",
  "duration_s": null,
  "captured_at": "2026-11-24T02:20:00Z"
}
```
- **Response Data (HTTP 201 Created):**
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "kind": "snapshot",
  "storage_key": "f/aaaaaaaa-0001-0001-0001-000000000001/evidence_7c9e6679.png",
  "size_bytes": 68,
  "sha256": "4c9444f6f890c29a67e5cf62a939f50682226f7a6dcf8f7f4803da5743b8be92",
  "captured_at": "2026-11-24T02:20:00Z"
}
```

### 2. `GET /api/v1/evidence`
- **Summary:** List Evidence Records
- **Query Parameters:**
  - `event_id`: Filter by event UUID
  - `incident_id`: Filter by incident UUID
  - `kind`: "snapshot" or "clip"
  - `page`: Page index (default 1)
  - `page_size`: Page size (default 20)

### 3. `GET /api/v1/evidence/{evidence_id}`
- **Summary:** Get Metadata for Single Evidence File

### 4. `GET /api/v1/evidence/{evidence_id}/download`
- **Summary:** Download Evidence Binary File
- **Response:** Raw binary streaming response with `Content-Type` matching recorded file and `Content-Disposition: attachment`.

### 5. `POST /api/v1/evidence/{evidence_id}/verify-integrity`
- **Summary:** Cryptographic SHA-256 Checksum Verification
- **Response Data:**
```json
{
  "evidence_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "is_valid": true,
  "calculated_sha256": "4c9444f6f890c29a67e5cf62a939f50682226f7a6dcf8f7f4803da5743b8be92",
  "recorded_sha256": "4c9444f6f890c29a67e5cf62a939f50682226f7a6dcf8f7f4803da5743b8be92",
  "verified_at": "2026-11-24T02:24:00Z"
}
```

---

## 6. Real-Time WebSocket AI Event Contracts

All clients connected via `/ws/v2/events?ticket=<ticket>` receive these real-time notifications:

### A. Action Requested (`ai_action_requested`)
```json
{
  "type": "ai_action_requested",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "data": {
    "action_id": "act-prop-01",
    "action_type": "create_incident",
    "initiated_by": "11111111-0001-0001-0001-000000000001"
  },
  "sent_at": "2026-11-24T02:24:00Z"
}
```

### B. Action Completed (`ai_action_completed`)
```json
{
  "type": "ai_action_completed",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "data": {
    "action_id": "act-prop-01",
    "status": "executed",
    "message": "Incident created successfully",
    "audit_reference": "AUDIT-20261124-E8B1A2"
  },
  "sent_at": "2026-11-24T02:24:00Z"
}
```

### C. Incident Created by AI (`incident_created`)
```json
{
  "type": "incident_created",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "data": {
    "incident_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "incident_type": "ppe_violation",
    "severity": "high",
    "state": "detected",
    "opened_at": "2026-11-24T02:24:00Z"
  },
  "sent_at": "2026-11-24T02:24:00Z"
}
```

### D. Alert Created by AI (`alert_created`)
```json
{
  "type": "alert_created",
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
  "data": {
    "alert_id": "4bb95f64-1234-4562-b3fc-2c963f66afa7",
    "incident_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "severity": "high",
    "status": "pending",
    "created_at": "2026-11-24T02:24:00Z"
  },
  "sent_at": "2026-11-24T02:24:00Z"
}
```

---

*Contract Approved — Ready for Toka's frontend integration and live production deployment.*
