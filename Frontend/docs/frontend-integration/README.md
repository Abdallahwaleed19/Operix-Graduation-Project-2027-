# Operix Frontend–Backend Integration Documentation

**Project:** Operix — Industrial AI Safety Platform  
**Stack:** React 19 + Vite + Bootstrap 5 + Chart.js + Fetch API + Native WebSockets  
**Backend:** FastAPI + SQLAlchemy + PostgreSQL + Redis  

---

## Architecture Overview

Operix follows a **PostgreSQL-driven, multi-tenant** architecture:
- All business data is scoped by `factory_id` extracted securely from the authenticated user context.
- API communication goes through `src/services/apiClient.js`, which handles:
  - Standardized envelope unwrapping (`{ status: "success", data, meta }`).
  - Uniform error handling (`{ status: "error", error_code, message, details }`).
  - Automatic `Authorization: Bearer <token>` and `X-Factory-Id` header injection.
  - Binary Blob downloads for reports and evidence files.
- **Dual-Mode Granularity (`isMockEnabled(module)`)**: Setting `VITE_USE_MOCK_DATA=false` activates live FastAPI integration **only** for verified connected modules (`analytics`, `assistant`, `reports`, `evidence`, `rules`, `websockets`), while pending modules (`S-1` through `S-4`) remain safely in UI-only preview mode until their backend endpoints land.

---

## Documentation Index

| File | Description |
| :--- | :--- |
| [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md) | Live status of all modules (Connected vs. Pending vs. Removed) |
| [API_ENDPOINTS.md](./API_ENDPOINTS.md) | Verified FastAPI endpoint contracts mapped to frontend services |
| [DATA_SOURCE_MAPPING.md](./DATA_SOURCE_MAPPING.md) | Mapping of every UI screen & component to PostgreSQL or Pending state |
| [WEBSOCKET_INTEGRATION.md](./WEBSOCKET_INTEGRATION.md) | Ticket-authenticated `/ws/v2/events` and `/ws/events` client guide |
| [DATABASE_DATA_FLOW.md](./DATABASE_DATA_FLOW.md) | End-to-end PostgreSQL -> FastAPI -> React data flow & tenant isolation |
| [FRONTEND_TESTING.md](./FRONTEND_TESTING.md) | Automated unit/integration tests and production build verification |
| [PENDING_BACKEND_DEPENDENCIES.md](./PENDING_BACKEND_DEPENDENCIES.md) | Missing backend APIs (S-1 to S-4) awaiting Core Backend implementation |

---

## Removed Features
- **Heatmaps & Tracking (`/heatmaps`)**: Permanently removed per project specification. Navigation links have been removed from `Sidebar.jsx` and routes redirect to `/analytics`.
