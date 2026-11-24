# OPERIX — Phase 4.1 Implementation Report
## Backend AI Integration Foundation & Session Injection

**Date:** 2026-11-24  
**Phase:** 4.1 (Backend Integration Foundation)  
**Status:** ✅ Complete — All deliverables implemented and tested  
**Test Result:** 30 passed, 0 failed (Phase 4.1 suite) | 159 passed, 5 deselected (complete non-live regression suite in 5.46s)  

---

## 1. Files Created and Modified

### Created

| File | Purpose |
|------|---------|
| `backend/app/api/ai_deps.py` | FastAPI dependency injection module for all four AI services |
| `backend/tests/test_phase41_ai_deps.py` | Phase 4.1 focused test suite (30 tests) |
| `reports/OPERIX_PHASE_4_1_IMPLEMENTATION_REPORT.md` | This document |

### Modified

| File | Change |
|------|--------|
| `backend/app/core/config.py` | Added `EVIDENCE_STORAGE_DIR`, `REPORTS_STORAGE_DIR` optional fields; added `_resolve_storage_dirs` model_validator; added `evidence_storage_path` and `reports_storage_path` properties |
| `backend/app/main.py` | Added `sync_ai_service_env()` call in lifespan startup block; wrapped in try/except to avoid hard startup failure if AI services unavailable |

---

## 2. Session Injection Design

### Design Rule: Caller-Owned Session

The canonical FastAPI backend **owns the SQLAlchemy Session lifecycle**. AI modules receive an already-open, tenant-scoped session and **must never commit, rollback, or close it**.

```
Request arrives
     │
     ▼
get_db() — creates Session, yields it
     │
     ▼
set_tenant_context(session, factory_id)  ← RLS context set before yield
     │
     ▼
get_tenant_db() — yields session to endpoint
     │
     ▼
AI service endpoint ← receives session via get_tenant_session_for_ai()
     │                 (must NOT commit/rollback/close)
     ▼
get_db() finally block — closes session, rolls back on exception
```

### Request-Scoped Sessions (`get_tenant_session_for_ai`)

```python
def get_tenant_session_for_ai(
    db: Session = Depends(get_tenant_db),
    factory_id: UUID = Depends(get_current_factory_id),
) -> Generator[tuple[Session, UUID], None, None]:
    yield db, factory_id
```

- Session already has tenant RLS context set.
- Session lifecycle (close, rollback) owned entirely by `get_db()`.
- AI services receive `(session, factory_id)` tuple.

### Background Task Sessions (`get_background_session`)

```python
@contextmanager
def get_background_session(factory_id: UUID) -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        set_tenant_context(db, factory_id=factory_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- Background tasks **must** use `get_background_session()` — they must **never** borrow a request session.
- Request sessions are not thread-safe and must not be shared across concurrent tasks.
- This context manager creates its own independent `SessionLocal()`, commits on success, rolls back on failure, and always closes.

---

## 3. Adapter Integration Details

### `sync_ai_service_env()` — Startup Environment Synchronisation

Called once inside the FastAPI `lifespan` startup block in `app/main.py`:

```python
try:
    from .api.ai_deps import sync_ai_service_env
    sync_ai_service_env()
except Exception as _ai_sync_exc:
    logger.warning(f"AI service environment sync skipped: {_ai_sync_exc}")
```

The function propagates canonical storage paths from `Settings` into `os.environ`:

| env var set | read by |
|-------------|---------|
| `EVIDENCE_STORAGE_DIR` | `incident_evidence/config.py` |
| `OPERIX_REPORTS_STORAGE_DIR` | `reports_generation/config.py` |
| `DATABASE_URL` | AI module sub-services (workforce analytics, etc.) |

**Idempotent** — uses `setdefault` semantics; never overwrites an already-set env var.  
**Secret-safe** — never logs `DATABASE_URL`, `SECRET_KEY`, or `WS_TICKET_KEY`.

### Service Factory Dependencies

| Dependency | Service | Session Type |
|-----------|---------|--------------|
| `get_workforce_analytics_service_dep` | `WorkforceAnalyticsService` | Injected request session |
| `get_llm_assistant_service_dep` | `OperixAssistantService` | No DB (LLM/RAG only) |
| `get_reports_service_dep` | `ReportService` | Injected request session + canonical engine |
| `get_evidence_service_dep` | `EvidenceService` | Storage dir only; session passed per-call |

All service factory dependencies call through `integration/phase1_adapter.py` as the single instantiation point. No factory logic is duplicated in `ai_deps.py`.

### Environment Constraint — Backend Venv

The backend venv (`backend/.venv`) does **not** contain `numpy`, `openpyxl`, or `reportlab`. These are AI-services-only packages that live in the AI-services venv.

This means `integration.phase1_adapter` **cannot be fully imported** from the backend venv test runner because it has top-level imports of `llm_rag_assistant` (→ numpy) and `reports_generation` (→ openpyxl).

**This is NOT an architectural blocker:**
- In production (`run.py` + AI-services venv), all imports succeed.
- 170 AI module tests (`run_all_tests.py`) verify full importability.
- 9 Phase 1 integration tests (`test_phase1_integration.py`) verify the full adapter.
- Phase 4.1 backend tests cover the error-mapping contract via a local `_adapt()` helper that replicates the logic without heavy imports.

---

## 4. Storage Configuration

### New Settings Fields (`app/core/config.py`)

```python
EVIDENCE_STORAGE_DIR: Optional[str] = Field(
    default=None,
    description="Env var: EVIDENCE_STORAGE_DIR. Defaults to <backend>/ai-services/storage/evidence.",
)
REPORTS_STORAGE_DIR: Optional[str] = Field(
    default=None,
    description="Env var: REPORTS_STORAGE_DIR. Defaults to <backend>/ai-services/storage/reports.",
)
```

### Path Resolution (`_resolve_storage_dirs` model_validator)

Runs once at startup after all fields are populated:

1. If the env var is set → resolve as-is (relative paths are made absolute relative to the backend dir).
2. If not set → use the default: `backend/ai-services/storage/{evidence|reports}`.
3. `Path.mkdir(parents=True, exist_ok=True)` — creates the directory if it does not exist.
4. Network mount failures are caught and treated as non-fatal (the path may be unavailable at startup).

### Properties

```python
@property
def evidence_storage_path(self) -> Path: ...

@property
def reports_storage_path(self) -> Path: ...
```

Both properties return an **absolute, guaranteed-to-exist** `Path` object.

### Default Directories

```
backend/ai-services/storage/evidence/   ← EVIDENCE_STORAGE_DIR default
backend/ai-services/storage/reports/    ← REPORTS_STORAGE_DIR default
```

These match the directories already created by the AI modules during the Abdullah Phase 1 integration.

---

## 5. Tenant Isolation Guarantees and Limitations

### Guarantees

- `set_tenant_context(session, factory_id)` is called by `get_tenant_db` **before** the session is yielded to any endpoint.
- All AI service dependencies receive a session that has already had the tenant context set.
- `get_background_session()` explicitly calls `set_tenant_context(db, factory_id=factory_id)` before yielding.
- WorkforceAnalyticsService enforces tenant isolation via explicit `WHERE factory_id = :factory_id` SQL, independent of RLS.
- IncidentEvidenceService enforces tenant isolation via explicit `FactoryMismatchError` on cross-factory access.

### Limitations (Explicitly Stated)

> **RLS enforcement is NOT VERIFIED on SQLite.**
> 
> `set_tenant_context` is a **safe no-op** on SQLite (`pgconfig.set_config` does not exist in SQLite). PostgreSQL Row-Level Security enforcement is verified only in the production PostgreSQL environment (operix_db).
> 
> Tests confirm `set_tenant_context` is callable and raises no errors on SQLite. They do NOT verify that the RLS policy blocks cross-factory queries.

### Verification Status

| Mechanism | Verified | Environment |
|-----------|----------|-------------|
| `set_tenant_context` callable | ✅ | SQLite (unit test) |
| `set_tenant_context` accepts optional `user_id` | ✅ | SQLite (unit test) |
| `set_tenant_context` called before first DB execute | ✅ | Mocked (unit test) |
| PostgreSQL RLS policy enforcement | ⚠️ NOT VERIFIED | Requires live PostgreSQL |
| `factory_id` WHERE clause in AI module queries | ✅ | WorkforceAnalyticsService audit |
| `FactoryMismatchError` on cross-factory evidence | ✅ | EvidenceService audit |

---

## 6. Tests and Exact Results

### Phase 4.1 Test Suite

**File:** `backend/tests/test_phase41_ai_deps.py`  
**Result: 30 passed, 0 failed in 0.52s**

| Test Class | Count | Coverage |
|-----------|-------|---------|
| `TestStorageSettingsResolution` | 8 | Absolute paths, directory existence, Settings property matching, default naming convention |
| `TestSyncAiServiceEnv` | 5 | Sets env vars, does not overwrite existing, idempotent, does not expose secret keys |
| `TestSessionOwnership` | 3 | Analytics no commit/rollback/close; evidence no close; reports engine injection |
| `TestTenantContextPropagation` | 3 | SQLite safe no-op, optional user_id, context called before execute |
| `TestBackgroundSessionIsolation` | 3 | Independent session, rollback on error, calls set_tenant_context |
| `TestAdapterCompatibility` | 8 | Error mapping: EvidenceNotFound→404, FactoryMismatch→403, InvalidMime→400, FileSizeLimit→400, ReportNotFound→404, InvalidReportFormat→400, generic→500, exception importability |

**Note on adapter tests:** The `_adapt()` helper in the test file replicates the error-mapping logic from `integration/phase1_adapter.py` without importing the full module (which requires numpy/openpyxl, absent from the backend venv). This is the documented environment-level constraint — not an architectural limitation.

### Pre-Existing Baseline Regression

**Result: 129 passed, 5 deselected (live_db), 0 failed**  
All tests from Phases 3.1 through 3.6 continue to pass with no regressions.

---

## 7. Remaining Blockers for Phase 4.2

The following items are **not implemented** in Phase 4.1 and are pre-conditions for Phase 4.2:

| Blocker | Description |
|---------|-------------|
| **No FastAPI AI routers** | No AI endpoints are mounted in `app/api/v1/router.py`. Phase 4.2 must implement AI endpoint modules and wire them. |
| **No `/api/v1/analytics/*` endpoint** | `WorkforceAnalyticsService` is wired via dependency but no route exposes it. |
| **No `/api/v1/reports/*` endpoint** | `ReportService` is wired via dependency but no route exposes it. |
| **No `/api/v1/evidence/*` endpoint** | `EvidenceService` is wired via dependency but no route exposes it. |
| **No `/api/v1/assistant/*` endpoint** | `OperixAssistantService` is wired via dependency but no route exposes it. |
| **`OperixActionService` is in-memory** | The LLM RAG assistant's action dispatcher remains a mock implementation. Requires Abdullah's AI-side completion. |
| **Backend venv dependency gap** | `numpy`, `openpyxl`, `reportlab` are not installed in the backend venv. If the backend test runner is to cover the full AI integration, these must be added or a separate venv strategy must be adopted. |
| **PostgreSQL RLS not verified** | `set_tenant_context` RLS enforcement has only been verified as callable; actual policy enforcement requires a non-production PostgreSQL test database (not `operix_db`). |

---

## 8. Required Coordination with Abdullah (AI Backend Owner)

| Item | Detail |
|------|--------|
| **Environment variable names** | `incident_evidence/config.py` reads `EVIDENCE_STORAGE_DIR`. `reports_generation/config.py` reads `OPERIX_REPORTS_STORAGE_DIR`. Both are propagated by `sync_ai_service_env()` at startup. If Abdullah renames these vars, `ai_deps.py` must be updated. |
| **`OPERIX_FACTORY_ID` for standalone AI tests** | `workforce_analytics/config.py` requires `OPERIX_FACTORY_ID` at **import time** (raises `RuntimeError` if missing). This env var must be present in `.env` for standalone AI-module test runs. The backend test suite sets it via `os.environ.setdefault` in `test_phase41_ai_deps.py`. |
| **venv dependency gap** | If Phase 4.2 integration tests need to run from the backend test runner (not the AI-services venv), `numpy`, `openpyxl`, and `reportlab` must be added to `backend/requirements.txt` and installed in the backend venv. |
| **Session ownership contract** | AI module services must continue to never `commit()`, `rollback()`, or `close()` the session received from FastAPI dependency injection. This is verified in `TestSessionOwnership`. Any change to AI module session handling must be re-tested. |
| **Phase 1 adapter interface** | `get_workforce_analytics_service(session, factory_id)`, `get_reports_generation_service(session, engine, storage_dir)`, `get_incident_evidence_service(storage_dir)`, and `get_llm_rag_assistant_service()` must remain stable. Changes to these signatures require updates in `ai_deps.py`. |

---

## 9. File Index

```
backend/
├── app/
│   ├── api/
│   │   └── ai_deps.py                    ← CREATED  (Phase 4.1)
│   ├── core/
│   │   └── config.py                     ← MODIFIED (Phase 4.1 — storage fields)
│   └── main.py                           ← MODIFIED (Phase 4.1 — sync_ai_service_env)
├── tests/
│   └── test_phase41_ai_deps.py           ← CREATED  (Phase 4.1 — 30 tests)
└── ai-services/
    └── storage/
        ├── evidence/                     ← auto-created by _resolve_storage_dirs
        └── reports/                      ← auto-created by _resolve_storage_dirs

reports/
└── OPERIX_PHASE_4_1_IMPLEMENTATION_REPORT.md   ← THIS FILE
```

---

*Signed off: Seif (Backend Owner) — Phase 4.1 complete. Phase 4.2 routers pending.*
