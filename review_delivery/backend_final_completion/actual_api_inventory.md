# Actual API Inventory (All Registered AI & Auth Endpoints)

All 21 endpoints are implemented and registered under `/api/v1` via `backend/app/api/v1/router.py`:

- **Auth:** `POST /api/v1/auth/ws-ticket`
- **Incident Evidence (5):** `POST /api/v1/evidence/upload`, `GET /api/v1/evidence`, `GET /api/v1/evidence/{evidence_id}`, `GET /api/v1/evidence/{evidence_id}/download`, `POST /api/v1/evidence/{evidence_id}/verify-integrity`
- **Workforce Analytics (6):** `GET /api/v1/analytics/overview`, `/attendance`, `/incidents`, `/productivity`, `/camera-coverage`, `/summary`
- **RAG Assistant (4):** `POST /api/v1/assistant/ask`, `GET /api/v1/assistant/sources`, `DELETE /api/v1/assistant/conversations/{conversation_id}`, `GET /api/v1/assistant/health`
- **AI Actions (1):** `POST /api/v1/assistant/actions/execute`
- **Reports Generation (4):** `POST /api/v1/reports/generate`, `GET /api/v1/reports`, `GET /api/v1/reports/{report_id}`, `GET /api/v1/reports/{report_id}/download`
