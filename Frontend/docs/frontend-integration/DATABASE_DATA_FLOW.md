# Database Data Flow & Multi-Tenant Isolation

**Single Source of Truth:** PostgreSQL (`operix_db`)  
**ORM / Session Layer:** SQLAlchemy (`backend/app/models/`) with `get_tenant_db` and `set_tenant_context`

---

## 1. End-to-End Flow

```text
PostgreSQL (operix_db)
  └── Canonical Models:
        - tenant.py: Factory, User, Role, FactoryMembership
        - operational.py: SafetyRule, Camera, Sensor, MonitoringZone, Department
        - incidents.py: Incident, Event, EvidenceFile, Alert
  └── FastAPI Services & Endpoints (/api/v1/*)
        - Extracts factory_id strictly from verified UserContext / JWT
        - Never trusts client-supplied factory_id overrides (returns 403 TENANT_ACCESS_DENIED)
        - Returns APIResponse { status: "success", data, meta }
  └── Frontend Services Layer (src/services/*)
        - apiClient.js unwraps payload.data and injects Authorization + X-Factory-Id
        - Services normalize response schemas (e.g. mapBackendRule) for React state
  └── React UI (src/pages/* & Chart.js)
        - Displays database-backed metrics, rules, reports, evidence, and RAG citations
```

---

## 2. Security & Integrity Guarantees
- **Tenant Isolation:** All queries in `analytics.py`, `assistant.py`, `reports.py`, `evidence.py`, `rules.py`, and `websockets.py` filter strictly by `factory_id`.
- **Evidence Integrity:** Uploaded evidence computes `SHA-256` checksums stored in `EvidenceFile` and validated on disk via `POST /api/v1/evidence/{id}/verify-integrity`.
- **AI Actions RBAC:** `POST /api/v1/assistant/actions/execute` validates user permissions and `idempotency_key` before modifying state.
