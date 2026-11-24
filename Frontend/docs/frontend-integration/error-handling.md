# Error Handling & Response Envelopes

**Source Files:** `backend/app/schemas/common.py`, `backend/app/core/errors.py`

---

## Standard Success Envelope (`APIResponse[T]`)
```json
{
  "status": "success",
  "data": {},
  "meta": {
    "request_timestamp": "2026-11-24T19:50:00Z",
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "api_version": "v1"
  }
}
```

## Standard Error Envelope (`APIErrorResponse`)
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Input validation failed.",
  "details": [
    { "field": "body.question", "issue": "String should have at least 2 characters" }
  ],
  "timestamp": "2026-11-24T19:50:00Z"
}
```

## HTTP Status Codes & Error Codes

| Status | `error_code` | Meaning |
|---:|---|---|
| `400` | `INVALID_BASE64`, `INVALID_EVIDENCE_PAYLOAD`, `INVALID_REPORT_REQUEST`, `ACTION_EXECUTION_FAILED` | Malformed request payload or domain validation error |
| `401` | `MISSING_AUTH_HEADER`, `INVALID_TOKEN`, `MISSING_CAMERA_KEY` | Missing, expired, or invalid credentials |
| `403` | `TENANT_ACCESS_DENIED`, `FORBIDDEN_FACTORY`, `INSUFFICIENT_PERMISSIONS` | Cross-factory access attempt or insufficient role privileges |
| `404` | `RESOURCE_NOT_FOUND` | Evidence, Incident, Sensor, or Report not found |
| `410` | `EVIDENCE_RESOURCE_GONE` | Evidence expired or purged |
| `422` | `VALIDATION_ERROR` | Pydantic request validation failure |
| `500` | `INTERNAL_SERVER_ERROR`, `AI_SUBSYSTEM_ERROR` | Unexpected backend or AI subsystem failure |
