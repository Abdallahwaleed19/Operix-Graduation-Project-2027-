# Frontend Integration Checklist (For Toka)

- [ ] Configure `VITE_API_BASE_URL` / `REACT_APP_API_BASE_URL` pointing to FastAPI backend (`http://localhost:8000`).
- [ ] Attach `Authorization: Bearer <token>` on all `/api/v1/*` requests.
- [ ] Handle `{ status: "error", error_code, message, details }` uniformly in API client.
- [ ] Integrate **Workforce Analytics** dashboard cards (`/api/v1/analytics/summary`, `/overview`, `/incidents`, `/productivity`, `/camera-coverage`).
- [ ] Integrate **Incident Evidence** upload (`POST /api/v1/evidence/upload`), list (`GET /api/v1/evidence`), download, and integrity check.
- [ ] Integrate **RAG Assistant** chat (`POST /api/v1/assistant/ask`) with `conversation_id` state & citation display.
- [ ] Integrate **AI Actions** confirmation buttons (`POST /api/v1/assistant/actions/execute`) with `idempotency_key` and RBAC error handling (`403 INSUFFICIENT_PERMISSIONS`).
- [ ] Integrate **Reports** generation (`POST /api/v1/reports/generate`), listing (`GET /api/v1/reports`), metadata (`GET /api/v1/reports/{report_id}`), and download (`GET /api/v1/reports/{report_id}/download`).
- [ ] Integrate **RAG Conversation Clear** (`DELETE /api/v1/assistant/conversations/{conversation_id}`).
