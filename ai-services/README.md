# Operix — Workforce Analytics Module

> **University Graduation Project — Menoufia National University 2026-2027**
> Faculty of Computers & Artificial Intelligence — Level 4
> Module owner: Abdallah Waleed

---

## Overview

This module implements **Workforce Analytics** for the Operix industrial safety platform.
It reads data from the existing Operix PostgreSQL database (`operix_db`) and exposes
reusable Python functions that the main FastAPI backend can call directly.

**No new tables are created. The existing schema is never modified.**

---

## Available Analytics

| Function | Returns | Notes |
|---|---|---|
| `get_workforce_overview()` | `WorkforceOverview` | Counts, role split |
| `calculate_attendance_metrics()` | `AttendanceMetrics` | ⚠ Proxy metric |
| `calculate_incident_analytics()` | `IncidentAnalytics` | Full incident breakdown |
| `calculate_productivity_metrics()` | `ProductivityMetrics` | ⚠ Proxy metric |
| `calculate_camera_coverage()` | `CameraCoverage` | Downtime from `unobserved_gaps` |
| `generate_workforce_summary()` | `WorkforceSummary` | Combines all five |

> [!NOTE]
> **Proxy metrics** — The Operix schema has no clock-in/out table, no shifts, and no task
> table. Attendance and productivity are therefore estimated from incident review/resolve
> activity. These are labelled clearly in every output dict.

---

## Schema Gaps (Documented)

| Metric | Available? | Reason |
|---|---|---|
| True attendance | ❌ | No clock-in/out / timesheet table |
| Working hours | ❌ | No work_logs / shifts table |
| Overtime | ❌ | No contracted-hours definition |
| Worker → department | ❌ | Users link to factory only; cameras carry dept |
| Task completion | ❌ | No task / assignment table |
| Attendance (proxy) | ✅ | Based on incident activity |
| Productivity (proxy) | ✅ | Based on incident review/resolve count |

---

## Project Structure

```
ai-services/
├── .env                          ← Real DB credentials (git-ignored)
├── .env.example                  ← Template — copy to .env
├── requirements.txt
├── run_demo.py                   ← Quick CLI demo
└── workforce_analytics/
    ├── __init__.py
    ├── config.py                 ← Env-var loading + constants
    ├── database.py               ← SQLAlchemy engine + session
    ├── models.py                 ← ORM stubs (documentation only)
    ├── repositories.py           ← All SELECT queries (raw SQL)
    ├── analytics.py              ← Public API functions
    ├── schemas.py                ← Pydantic v2 output models
    ├── sample_data_seed.sql      ← Sample data (already inserted)
    └── tests/
        ├── __init__.py
        └── test_analytics.py     ← pytest suite (30+ tests)
```

---

## Windows Setup

### Requirements

- Python 3.14 (from `C:\Users\<you>\AppData\Local\Programs\Python\Python314\`)
- PostgreSQL 18 running on `localhost:5432`
- Database `operix_db` already created and seeded

### 1 — Clone / navigate to the module

```powershell
cd "d:\...\Operix\ai-services"
```

### 2 — Create virtual environment

```powershell
"C:\Users\<YourName>\AppData\Local\Programs\Python\Python314\python.exe" -m venv .venv
```

### 3 — Install dependencies

```powershell
.\.venv\Scripts\pip install sqlalchemy "psycopg[binary]" pydantic python-dotenv pytest pytest-asyncio
```

### 4 — Configure `.env`

Copy the example and fill in your credentials:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```
DATABASE_URL=postgresql+psycopg://postgres:abdallah@localhost:5432/operix_db
DEFAULT_FACTORY_ID=aaaaaaaa-0001-0001-0001-000000000001
LOW_PRODUCTIVITY_THRESHOLD=2
HIGH_PRODUCTIVITY_THRESHOLD=5
RESOLUTION_RATE_TARGET=0.80
```

> [!CAUTION]
> Never commit `.env` to Git — it contains your database password.
> The `.gitignore` already excludes it.

### 5 — Run the demo

```powershell
.\.venv\Scripts\python run_demo.py
```

Expected output:

```
=================================================================
  Operix — Workforce Analytics Demo
=================================================================
[OK] Database connection successful.

── A. WORKFORCE OVERVIEW ─────────────────────────────────────
  Total users    : 8
  Active workers : 7
  Inactive       : 1
  By role        : {'factory_admin': 1, 'factory_manager': 2, 'safety_supervisor': 4}

── B. ATTENDANCE (proxy) ──────────────────────────────────────
  Members with activity : 6 / 8
  Activity rate         : 75.0%

── C. INCIDENT ANALYTICS ──────────────────────────────────────
  Total incidents      : 15
  Resolved             : 7
  Resolution rate      : 46.67%
  Target met (≥80%)    : False

── D. PRODUCTIVITY METRICS ────────────────────────────────────
  Workers analysed     : 7
  Avg handled/worker   : ...

── E. CAMERA COVERAGE ─────────────────────────────────────────
  Total cameras        : 4
  Active / Inactive    : 3 / 1
  Overall coverage     : ...%
```

### 6 — Run automated tests

```powershell
.\.venv\Scripts\pytest workforce_analytics/tests/test_analytics.py -v
```

---

## FastAPI Integration Guide

### Install in the main backend

Add to the backend's `requirements.txt` (or install directly):

```
sqlalchemy>=2.0
psycopg[binary]>=3.2
pydantic>=2.9
python-dotenv>=1.0
```

Copy the `workforce_analytics/` folder into the FastAPI project root (or install as a package).

### Example FastAPI routes

```python
# backend/routers/analytics.py
from fastapi import APIRouter
from uuid import UUID
from workforce_analytics.analytics import (
    get_workforce_overview,
    calculate_attendance_metrics,
    calculate_incident_analytics,
    calculate_productivity_metrics,
    calculate_camera_coverage,
    generate_workforce_summary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

FACTORY_ID = UUID("aaaaaaaa-0001-0001-0001-000000000001")

@router.get("/overview")
def overview():
    return get_workforce_overview(FACTORY_ID).model_dump(mode="json")

@router.get("/incidents")
def incidents():
    return calculate_incident_analytics(FACTORY_ID).model_dump(mode="json")

@router.get("/productivity")
def productivity():
    return calculate_productivity_metrics(FACTORY_ID).model_dump(mode="json")

@router.get("/cameras")
def cameras():
    return calculate_camera_coverage(FACTORY_ID).model_dump(mode="json")

@router.get("/summary")
def summary():
    return generate_workforce_summary(FACTORY_ID).model_dump(mode="json")
```

Register in `main.py`:

```python
from backend.routers import analytics
app.include_router(analytics.router)
```

### Date range filtering

All analytics functions accept optional `start` and `end` datetime parameters:

```python
from datetime import datetime, timezone, timedelta

end   = datetime.now(tz=timezone.utc)
start = end - timedelta(days=30)

result = calculate_incident_analytics(factory_id, start=start, end=end)
```

### JSON output example

```json
{
  "generated_at": "2026-11-20T00:00:00+00:00",
  "total_workers": 7,
  "inactive_workers": 1,
  "activity_rate_pct": 75.0,
  "total_incidents": 15,
  "resolved_incidents": 7,
  "resolution_rate_pct": 46.67,
  "avg_resolve_time_hrs": 12.5,
  "avg_handled_per_worker": 3.14,
  "camera_coverage_pct": 97.8
}
```

---

## Security Notes

- All DB credentials are loaded from `.env` via `python-dotenv`.
- Never hardcode passwords or API keys in source files.
- Never commit `.env` to Git.
- The analytics module only issues `SELECT` statements — no writes to the DB.
- All test runs use mock data or the sample seed — never destructive operations.

---

## Sample Data

Sample data was inserted via `workforce_analytics/sample_data_seed.sql`.

Counts after seeding:

| Table | Count |
|---|---|
| `factories` | 1 |
| `users` | 8 |
| `factory_memberships` | 8 |
| `departments` | 3 |
| `cameras` | 4 |
| `monitoring_zones` | 2 |
| `safety_rules` | 3 |
| `incidents` | 15 |
| `events` | 15 |
| `unobserved_gaps` | 3 |

To verify:

```powershell
$env:PGPASSWORD='abdallah'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d operix_db -p 5432 -c "SELECT COUNT(*) FROM incidents WHERE factory_id='aaaaaaaa-0001-0001-0001-000000000001';"
```

---

## Checklist

- [x] PHASE 1: ERD + schema analysis complete
- [x] PHASE 2: Sample data plan reviewed
- [x] PHASE 3: Sample data inserted (15 incidents, 8 users, 4 cameras)
- [x] PHASE 4: Python module implemented (`analytics.py`, `repositories.py`, `schemas.py`)
- [ ] PHASE 5: Tests run and passing ← **run `.\.venv\Scripts\pytest ... -v`**
- [x] PHASE 6: README + integration docs complete
