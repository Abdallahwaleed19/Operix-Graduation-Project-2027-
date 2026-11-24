# Operix — Core Backend Infrastructure

**Academic Year:** 2026–2027  
**System:** Operix Industrial AI Safety Platform  
**Backend Lead:** Seif Sameh  
**Framework:** FastAPI | Python 3.11+ / 3.14 | SQLAlchemy 2.0 | PostgreSQL 16+ (psycopg3)

---

## 1. Architecture & Directory Layout

```text
backend/
├── .env.example                     # Standardized environment template
├── requirements.txt                 # Pinned core production & test dependencies
├── run.py                           # CLI entrypoint to launch Uvicorn development server
├── README.md                        # Setup and developer documentation
├── app/
│   ├── main.py                      # FastAPI application factory, lifespan, CORS, and routers
│   ├── core/
│   │   ├── config.py                # Pydantic v2 Settings, env loading, CORS parsing
│   │   ├── database.py              # SQLAlchemy 2.0 engine, SessionLocal, RLS context, health ping
│   │   ├── errors.py                # Standardized JSON error envelopes & global exception handlers
│   │   └── logging.py               # Structured logging configuration
│   ├── models/                      # 1:1 SQLAlchemy models mirroring Mohamed Salah's 20 tables
│   │   ├── base.py                  # DeclarativeBase, UUID primary key, timestamp mixins
│   │   ├── enums.py                 # 15 PostgreSQL ENUM types mapped to Python Enums
│   │   ├── tenant.py                # factories, users, auth_tokens, roles, permissions, etc.
│   │   ├── operational.py           # departments, cameras, sensors, monitoring_zones, safety_rules, etc.
│   │   └── incidents.py             # incidents, events, evidence_files, alerts, notification_targets, etc.
│   ├── schemas/
│   │   ├── common.py                # Generic APIResponse[T], APIResponseMeta, APIErrorResponse
│   │   └── health.py                # HealthData, DatabaseHealth schemas
│   └── api/
│       ├── deps.py                  # FastAPI dependency injection (get_db, tenant context)
│       └── v1/
│           ├── router.py            # Aggregated v1 API router
│           └── endpoints/
│               └── health.py        # /health, /health/live, /api/v1/health endpoints
├── tests/
│   ├── conftest.py                  # Pytest fixtures and TestClient configuration
│   ├── test_config.py               # Settings and CORS validation tests
│   ├── test_models.py               # 20-table SQLAlchemy reflection & Enum mapping tests
│   ├── test_health.py               # Health, readiness, and OpenAPI schema tests
│   └── test_errors.py               # Standardized error envelope tests
└── ai-services/                     # Abdullah's AI Subsystems (Untouched / Preserved)
    ├── llm_rag_assistant/
    └── workforce_analytics/
```

---

## 2. Quickstart Guide (Windows PowerShell)

### Step 1 — Activate the Virtual Environment
```powershell
cd d:\VS_Works\project_MNU\Operix-Graduation-Project-2027-\backend
.\.venv\Scripts\Activate.ps1
```

### Step 2 — Environment Variables & Required Services
Copy `.env.example` to create your local `.env`:
```powershell
Copy-Item .env.example .env
```
**Runtime Prerequisites:**
- **Redis (Required):** The FastAPI lifespan verifies Redis connectivity on startup (`REDIS_URL`, default `redis://localhost:6379/0`) and fails closed if Redis is unreachable (required for `/api/v1/auth/ws-ticket` and `/ws/v2/events`).
- **PostgreSQL:** Set `DATABASE_URL` in `.env` (never use production `operix_db` for automated tests).
- **Required Security & CORS Variables:**
  - `SECRET_KEY` (32+ bytes) — signs human access JWTs.
  - `WS_TICKET_KEY` (32+ bytes, **must differ** from `SECRET_KEY`) — signs short-lived WebSocket tickets.
  - `ALLOWED_ORIGINS` — defaults to `http://localhost:5173,http://127.0.0.1:5173` for the Vite React frontend (applied to both REST CORS and WebSocket `Origin` checks).
  - `EVIDENCE_STORAGE_DIR` / `REPORTS_STORAGE_DIR` — storage roots for evidence and report artifacts.
  - `ALLOW_TEST_AUTH_FALLBACK` — keep `false` outside automated offline tests.

### Step 3 — Run Automated Tests
Execute the full automated test suite:
```powershell
# When inside the backend directory:
$env:PYTHONPATH="."
pytest tests -v

# Or when running from the repository root (Operix-Graduation-Project-2027-):
# $env:PYTHONPATH="backend"
# pytest backend\tests -v
```

### Step 4 — Launch the FastAPI Development Server
Ensure Redis is running locally, then start Uvicorn from `backend/`:
```powershell
python run.py
```
Or directly with Uvicorn:
```powershell
$env:PYTHONPATH=".;ai-services"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The Vite frontend (`http://localhost:5173` / `http://127.0.0.1:5173`) can then call `/api/v1/*` and connect to `ws://127.0.0.1:8000/ws/v2/events?ticket=<ws_ticket>`.

---

## 3. Verified Endpoints & Documentation

Once the server is running, explore the interactive documentation:
- **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON Schema:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)
- **Liveness Probe:** [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- **Full Health & Subsystems Diagnostic:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **CV Event Ingestion API:** `POST /api/v1/events/ingest` & `POST /api/v1/events/batch`
- **Real-Time WebSocket Stream:** `ws://127.0.0.1:8000/ws/events?factory_id=<UUID>`

---

## 4. Computer Vision Event Ingestion & WebSockets (Phase 2 Hardening)

### A. Authenticated CV Ingestion API (`POST /api/v1/events/ingest`)
Requires `X-Camera-Key` authentication header matching authorized camera credentials.
Directly compatible with the CV Team Guide (§6). Sample request:
```http
POST /api/v1/events/ingest HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json
X-Camera-Key: operix-dev-cv-key-change-in-production-2027
X-Factory-Id: 00000000-0000-0000-0000-000000000001
```
```json
{
  "event_id": "9d2f7a11-3b6c-4d85-b3a9-5e0c1f2a7d44",
  "event_type": "ppe_violation",
  "event_state": "started",
  "module": "ppe_detection",
  "camera_id": "camera_01",
  "timestamp": "2026-11-23T00:30:00Z",
  "frame_index": 880,
  "frame_size": [2304, 1296],
  "bbox": [600.0, 250.0, 790.0, 840.0],
  "confidence": 0.88,
  "attributes": {
    "helmet": false,
    "safety_vest": true,
    "missing": ["helmet"]
  }
}
```

### B. Authenticated Real-Time WebSocket for Toka's Frontend (`ws://.../ws/events`)
Requires cryptographic token authentication: `ws://127.0.0.1:8000/ws/events?token=<access_token>&factory_id=<UUID>`

1. **Connection Rejection Codes:**
- `4401`: Missing, invalid, or expired cryptographic token.
- `4403`: Cross-tenant attempt (token tenant scope does not match requested `factory_id`).

2. **Initial Handshake (Code 1000):**
```json
{
  "type": "connection_established",
  "factory_id": "00000000-0000-0000-0000-000000000001",
  "user_id": "user-uuid",
  "status": "connected",
  "message": "Connected to Operix real-time safety stream."
}
```

3. **Real-Time Broadcast Event (pushed on violation):**
```json
{
  "type": "safety_event",
  "factory_id": "00000000-0000-0000-0000-000000000001",
  "data": {
    "event_id": "9d2f7a11-3b6c-4d85-b3a9-5e0c1f2a7d44",
    "event_type": "ppe_violation",
    "event_state": "started",
    "module": "ppe_detection",
    "camera_id": "camera_01",
    "timestamp": "2026-11-23T00:30:00Z",
    "confidence": 0.88,
    "bbox_normalized": [0.2604, 0.1929, 0.0825, 0.4552],
    "details": { ... }
  },
  "sent_at": "2026-11-23T00:30:00.123Z"
}
```

### C. Database-Level Idempotency
Ingestion enforces database-level atomic UPSERT (`INSERT INTO events (...) ON CONFLICT (id) DO NOTHING`). Duplicate submissions are recognized atomically without race conditions, returning `duplicate_ignored` with `broadcast=false`.

---

## 5. Standard API Envelope Specification

All Operix API endpoints return predictable response envelopes:

### Success Envelope
```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "factory_id": "00000000-0000-0000-0000-000000000001",
    "timestamp": "2026-11-22T15:30:00Z",
    "api_version": "v1"
  }
}
```

### Error Envelope
```json
{
  "status": "error",
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Camera with id 'cam-01' was not found.",
  "details": [],
  "timestamp": "2026-11-22T15:30:00Z"
}
```
