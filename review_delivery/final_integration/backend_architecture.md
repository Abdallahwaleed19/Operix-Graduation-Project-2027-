# Backend Architecture Synchronization

- **Entrypoint:** `backend/app/main.py` (`create_application()`, `lifespan()` calling `sync_ai_service_env()`, DB check, Redis pool init).
- **Router Registration:** `backend/app/api/v1/router.py` mounts `analytics.router`, `assistant.router`, `reports.router`, `evidence.router` under `API_V1_STR = "/api/v1"`.
- **Auth & Tenant Context:** `backend/app/api/deps.py` provides `get_current_user_context` -> `AuthenticatedUser(user_id, factory_id, role, full_name, email)` and `get_tenant_db` (sets PostgreSQL RLS tenant context).
- **AI Dependency Providers:** `backend/app/api/ai_deps.py` provides `get_workforce_analytics_service_dep`, `get_llm_assistant_service_dep`, `get_reports_service_dep`, `get_evidence_service_dep`, `get_background_session`, and storage paths via `backend/ai-services/integration/phase1_adapter.py`.
- **AI Actions:** `backend/app/services/ai_action_service.py` (`AIActionService`) executes real `Incident`, `Alert`, and `Sensor` mutations and stages WebSocket broadcasts.
