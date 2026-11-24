# Operix — Frontend API Integration Documentation (For Toka)

**Platform:** Operix Industrial AI Safety Platform  
**API Base Prefix:** `/api/v1` (configured via `settings.API_V1_STR`)  
**Default Local Base URL:** `http://localhost:8000`  
**OpenAPI Specification:** Exported directly from `app.main.create_application().openapi()` (`32` paths, all `21` expected Frontend endpoints verified) in [`openapi.json`](./openapi.json).

---

## Documentation Index

| File | Description |
|---|---|
| [`authentication.md`](./authentication.md) | JWT Bearer auth, `X-Factory-Id` header, and WebSocket ticket issuance |
| [`incident-evidence-api.md`](./incident-evidence-api.md) | Upload, list, metadata, download, and SHA-256 integrity verification |
| [`workforce-analytics-api.md`](./workforce-analytics-api.md) | Overview, attendance, incidents, productivity, camera coverage, and summary |
| [`rag-assistant-api.md`](./rag-assistant-api.md) | Bilingual RAG Q&A, source citations, conversation clear, and health |
| [`reports-api.md`](./reports-api.md) | PDF/Excel report generation, listing, metadata, and download |
| [`ai-actions-api.md`](./ai-actions-api.md) | Agentic remediation action execution & RBAC rules |
| [`error-handling.md`](./error-handling.md) | Standardized `APIResponse` / `APIErrorResponse` envelopes & status codes |
| [`frontend-integration-guide.md`](./frontend-integration-guide.md) | React/Fetch setup, base URL, auth headers, and component patterns |
| [`api-contracts.json`](./api-contracts.json) | Machine-readable endpoint & schema contract summary |
| [`frontend-api-examples.js`](./frontend-api-examples.js) | Reusable JS API client & example calls for all AI modules |
| [`frontend-integration-checklist.md`](./frontend-integration-checklist.md) | Step-by-step integration checklist for Toka |

---

## Endpoint Readiness Status

| Module | Endpoint | Status |
|---|---|---|
| **Auth** | `POST /api/v1/auth/ws-ticket` | Implemented & registered |
| **Incident Evidence** | `POST /api/v1/evidence/upload`, `GET /api/v1/evidence`, `GET /api/v1/evidence/{evidence_id}`, `GET /api/v1/evidence/{evidence_id}/download`, `POST /api/v1/evidence/{evidence_id}/verify-integrity` | Implemented & registered |
| **Workforce Analytics** | `GET /api/v1/analytics/overview`, `/attendance`, `/incidents`, `/productivity`, `/camera-coverage`, `/summary` | Implemented & registered |
| **RAG Assistant** | `POST /api/v1/assistant/ask`, `GET /api/v1/assistant/sources`, `GET /api/v1/assistant/health` | Implemented & registered |
| **RAG Assistant** | `DELETE /api/v1/assistant/conversations/{conversation_id}` | Implemented & registered (Seif `cdda98c` ownership & 403 handling) |
| **AI Actions** | `POST /api/v1/assistant/actions/execute` | Implemented & registered |
| **Reports** | `POST /api/v1/reports/generate`, `GET /api/v1/reports` | Implemented & registered |
| **Reports** | `GET /api/v1/reports/{report_id}`, `GET /api/v1/reports/{report_id}/download` | Implemented & registered (Seif `cdda98c` passes `factory_id=user.factory_id`) |
