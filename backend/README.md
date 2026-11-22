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

### Step 2 — Environment Variables Configuration
Copy `.env.example` to create your local `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your local PostgreSQL connection string is set in `.env`:
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/operix_db
DEFAULT_FACTORY_ID=00000000-0000-0000-0000-000000000001
DEBUG=True
```

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
```powershell
python run.py
```
Or directly with Uvicorn:
```powershell
$env:PYTHONPATH="backend;backend/ai-services"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 3. Verified Endpoints & Documentation

Once the server is running, explore the interactive documentation:
- **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON Schema:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)
- **Liveness Probe:** [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- **Full Health & Subsystems Diagnostic:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 4. Standard API Envelope Specification

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
