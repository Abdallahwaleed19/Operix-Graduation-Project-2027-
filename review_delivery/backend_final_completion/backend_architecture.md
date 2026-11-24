# Backend Architecture Verification

- **FastAPI App (`backend/app/main.py`):** Configures CORS, global error handlers (`register_error_handlers`), `lifespan()` syncing `EVIDENCE_STORAGE_DIR` and `OPERIX_REPORTS_STORAGE_DIR`, DB check, and Redis pool.
- **Router Registration (`backend/app/api/v1/router.py`):** Mounts `health`, `auth`, `events`, `rules`, `websockets`, `analytics`, `assistant`, `reports`, `evidence` under `/api/v1`.
- **Auth & Tenant Isolation (`backend/app/api/deps.py`):** `get_current_user_context` validates Bearer JWT, rejects `X-Factory-Id` mismatch (`403 FORBIDDEN_FACTORY`), and `get_tenant_db` sets PostgreSQL RLS tenant context.
- **AI Dependency Injection (`backend/app/api/ai_deps.py`):** Injects canonical `Session` and `Engine` via `integration/phase1_adapter.py`; provides `get_background_session()`.
- **AI Actions (`backend/app/services/ai_action_service.py`):** Executes real `Incident`, `Alert`, `Sensor` operations and stages post-commit WebSocket broadcasts.
