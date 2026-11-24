# Actual API Inventory (AI & Auth Endpoints)

All mounted under `/api/v1` via `backend/app/api/v1/router.py`:

- **Auth:** `POST /api/v1/auth/ws-ticket`
- **Evidence:** `POST /api/v1/evidence/upload`, `GET /api/v1/evidence`, `GET /api/v1/evidence/{evidence_id}`, `GET /api/v1/evidence/{evidence_id}/download`, `POST /api/v1/evidence/{evidence_id}/verify-integrity`
- **Workforce Analytics:** `GET /api/v1/analytics/overview`, `/attendance`, `/incidents`, `/productivity`, `/camera-coverage`, `/summary`
- **RAG Assistant:** `POST /api/v1/assistant/ask`, `GET /api/v1/assistant/sources`, `DELETE /api/v1/assistant/conversations/{conversation_id}` *(pending Seif approval)*, `GET /api/v1/assistant/health`
- **AI Actions:** `POST /api/v1/assistant/actions/execute`
- **Reports:** `POST /api/v1/reports/generate`, `GET /api/v1/reports`, `GET /api/v1/reports/{report_id}` *(blocked)*, `GET /api/v1/reports/{report_id}/download` *(blocked)*
