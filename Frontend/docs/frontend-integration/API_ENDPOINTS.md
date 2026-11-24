# Operix Verified FastAPI Endpoints

All endpoints below are verified against `docs/frontend-integration/openapi.json` and the live FastAPI routers in `backend/app/api/v1/router.py`.

---

## A. Workforce Analytics (`/api/v1/analytics`)
- `GET /api/v1/analytics/overview` — Factory-wide safety & productivity KPIs.
- `GET /api/v1/analytics/summary` — High-level operational summary.
- `GET /api/v1/analytics/attendance` — Shift and workforce attendance metrics.
- `GET /api/v1/analytics/incidents` — Incident trend breakdown by severity/type.
- `GET /api/v1/analytics/productivity` — Productivity output metrics per department.
- `GET /api/v1/analytics/camera-coverage` — Camera uptime and zone coverage telemetry.

## B. AI Assistant & Actions (`/api/v1/assistant`)
- `POST /api/v1/assistant/ask` — RAG-powered safety assistant query; returns answer, `citations[]`, and `suggested_actions[]`.
- `GET /api/v1/assistant/sources` — List indexed safety knowledge-base sources.
- `DELETE /api/v1/assistant/conversations/{conversation_id}` — Delete user conversation (enforces `(factory_id, user_id)` ownership).
- `GET /api/v1/assistant/health` — RAG vector store and LLM service health status.
- `POST /api/v1/assistant/actions/execute` — Execute authorized AI action via `AIActionService.execute_action()` with RBAC & idempotency key.

## C. Reports (`/api/v1/reports`)
- `POST /api/v1/reports/generate` — Generate safety/compliance report (`pdf` or `xlsx`).
- `GET /api/v1/reports` — List generated reports scoped to `factory_id`.
- `GET /api/v1/reports/{report_id}` — Fetch single report metadata.
- `GET /api/v1/reports/{report_id}/download` — Authenticated binary download.

## D. Incident Evidence (`/api/v1/evidence`)
- `POST /api/v1/evidence/upload` — Upload snapshot/clip (`file_base64`, `event_id`, `kind`, `content_type`), computes SHA-256.
- `GET /api/v1/evidence` — List evidence records filtered by `event_id`, `incident_id`, `kind`.
- `GET /api/v1/evidence/{evidence_id}` — Fetch evidence metadata.
- `GET /api/v1/evidence/{evidence_id}/download` — Protected binary blob download.
- `POST /api/v1/evidence/{evidence_id}/verify-integrity` — Recomputes disk SHA-256 against PostgreSQL record.

## E. Safety Rules (`/api/v1/rules`)
- `POST /api/v1/rules` — Create `SafetyRule` (`SafetyRuleCreate` with scope exclusivity).
- `GET /api/v1/rules` — List rules (`is_enabled`, `event_type`, `limit`, `offset`).
- `GET /api/v1/rules/{rule_id}` — Get rule details.
- `PUT /api/v1/rules/{rule_id}` — Update rule (`SafetyRuleUpdate`) and increment version.
- `PATCH /api/v1/rules/{rule_id}/status` — Toggle `is_enabled` state.
- `DELETE /api/v1/rules/{rule_id}` — Delete rule.

## F. WebSockets & Auth Tickets
- `POST /api/v1/auth/ws-ticket` — Issue single-use 60s Redis-backed WebSocket ticket.
- `WS /ws/v2/events?ticket=<ticket>` — Primary ticket-authenticated real-time event stream.
- `WS /ws/events?token=<jwt>&factory_id=<uuid>` — Legacy JWT-authenticated fallback stream.
