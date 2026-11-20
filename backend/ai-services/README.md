# Operix — Workforce Analytics Service & API Contracts

> **University Graduation Project — Menoufia National University 2026-2027**  
> Faculty of Computers & Artificial Intelligence — Level 4  
> **Module Owner:** Abdallah Waleed  
> **Backend Integration Lead:** Seif Sameh (FastAPI)  
> **Frontend Integration Lead:** Toka (HTML/CSS/JS Dashboard)  

---

## 1. Overview & Architecture

This package provides an **independent, production-ready Workforce Analytics Service** for the Operix Industrial AI Safety platform. It queries the PostgreSQL 18 database (`operix_db`) without modifying its schema, calculates core workforce and safety metrics, and exposes typed interfaces for both Seif's FastAPI backend and Taqi's frontend dashboard.

```
┌─────────────────────────────────────────────────────────┐
│              Toka's Frontend Dashboard                  │
│             (HTML5 / CSS3 / JavaScript)                 │
└────────────────────────────┬────────────────────────────┘
                             │ HTTP REST API (JSON)
┌────────────────────────────▼────────────────────────────┐
│              Seif's FastAPI Main Backend                │
│                 (/api/v1/analytics/*)                   │
└────────────────────────────┬────────────────────────────┘
                             │ Python Method Calls
┌────────────────────────────▼────────────────────────────┐
│            WorkforceAnalyticsService (Facade)           │
│    (backend/ai-services/workforce_analytics/services)   │
└──────────────┬───────────────────────────┬──────────────┘
               │                           │
┌──────────────▼──────────────┐ ┌──────────▼──────────────┐
│  Core Analytics Algorithms  │ │   Pydantic v2 Schemas    │
│       (analytics.py)        │ │  & Request/Response DTOs │
└──────────────┬──────────────┘ └─────────────────────────┘
               │
┌──────────────▼──────────────┐
│ Raw SQL Repositories (text) │
└──────────────┬──────────────┘
               │ SQLAlchemy 2.x / Psycopg
┌──────────────▼──────────────┐
│  PostgreSQL 18 (operix_db)  │
└─────────────────────────────┘
```

---

## 2. Project Directory Structure

```
backend/ai-services/
├── .env                              ← Real DB credentials (git-ignored)
├── .env.example                      ← Template — copy to .env
├── requirements.txt                  ← Dependencies specification
├── run_demo.py                       ← Direct CLI demo of analytics functions
├── run_tests.py                      ← Comprehensive 64-test automated suite (zero extra dependencies)
├── integration/
│   ├── __init__.py
│   └── analytics_demo.py             ← Service layer demo without a running FastAPI server
└── workforce_analytics/
    ├── __init__.py
    ├── config.py                     ← Environment loading & threshold constants
    ├── database.py                   ← SQLAlchemy engine & thread-safe get_session()
    ├── models.py                     ← Database schema documentation stubs (ORM)
    ├── repositories.py               ← Raw SELECT SQL query layer (read-only)
    ├── analytics.py                  ← 6 Core analytics calculation algorithms
    ├── schemas.py                    ← Core Pydantic v2 domain schemas
    ├── sample_data_seed.sql          ← Seed data for testing (15 incidents, 8 users, 4 cameras)
    ├── services/
    │   ├── __init__.py
    │   └── analytics_service.py      ← Independent WorkforceAnalyticsService Facade
    ├── api_contracts/
    │   ├── __init__.py
    │   ├── requests.py               ← Query parameter validation models
    │   └── responses.py              ← Standard API envelope & response DTOs
    └── tests/
        ├── __init__.py
        ├── test_analytics.py         ← Pytest suite
        └── test_service.py           ← Service layer & API contract tests
```

---

## 3. Supported Analytics & Schema Gaps

| Metric Operation | Function / Endpoint | Availability | Documented Rationale / Formula |
|---|---|:---:|---|
| **Workforce Overview** | `get_workforce_overview()` | ✅ **Full** | User counts, active status, role split (Admin, Manager, Supervisor). |
| **Attendance Analytics** | `get_attendance_metrics()` | ⚠ **Proxy** | Proxied from incident review/resolve activity. True clock-in/out table is absent in schema. |
| **Safety Incidents** | `get_incident_analytics()` | ✅ **Full** | Total incidents, resolution rate, response times, breakdowns by type, severity, and state. |
| **Worker Productivity** | `get_productivity_metrics()` | ⚠ **Proxy** | Throughput of incidents reviewed and resolved per worker with configurable thresholds. |
| **Camera Coverage** | `get_camera_coverage()` | ✅ **Full** | Uptime percentage and downtime hours per camera and department via `unobserved_gaps`. |
| **Unified Summary** | `get_workforce_summary()` | ✅ **Full** | Consolidates all 5 metrics into a single unified dashboard payload. |
| **Working Hours & Shifts**| — | ❌ **Gapped** | No timesheets, shifts, or clock-in/out tables exist in the schema. |
| **Worker ↔ Department** | — | ❌ **Gapped** | Users link to factories only; only cameras/sensors carry `department_id`. |

---

## 4. API Contract Specifications (For Seif & Taqi)

All endpoints conform to the standard Operix API response envelope:

```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "request_timestamp": "2026-11-20T09:10:38Z",
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "api_version": "v1"
  }
}
```

### Endpoints Matrix

#### 1. `GET /api/v1/analytics/workforce`
- **Purpose:** Current snapshot of workers, active count, and role distribution.
- **Query Parameters:**
  - `factory_id` *(optional UUID)*: Target factory. Defaults to configured factory.
- **Date Filtering:** Not supported (workforce snapshot is current state).
- **Example Response Data:**
  ```json
  {
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "total_users": 8,
    "active_workers": 7,
    "inactive_workers": 1,
    "invited_users": 0,
    "disabled_users": 1,
    "by_role": {
      "factory_admin": 1,
      "factory_manager": 2,
      "safety_supervisor": 4
    }
  }
  ```

#### 2. `GET /api/v1/analytics/attendance`
- **Purpose:** Attendance and activity rate proxied from review/resolve activity.
- **Query Parameters:**
  - `factory_id` *(optional UUID)*
  - `start_date` *(optional ISO 8601 datetime, e.g., `2026-11-01T00:00:00Z`)*
  - `end_date` *(optional ISO 8601 datetime)*
- **Validation:** `start_date` must be earlier than or equal to `end_date`.
- **Example Response Data:**
  ```json
  {
    "total_members": 8,
    "members_with_activity": 6,
    "members_no_activity": 2,
    "activity_rate_pct": 75.0,
    "daily_activity_trend": [
      { "date": "2026-11-10", "active_users": 3 },
      { "date": "2026-11-11", "active_users": 4 }
    ],
    "data_quality_note": "PROXY METRIC — based on incident review/resolve activity."
  }
  ```

#### 3. `GET /api/v1/analytics/incidents`
- **Purpose:** Incident counts, resolution rate, and response times.
- **Query Parameters:**
  - `factory_id` *(optional UUID)*
  - `start_date` *(optional ISO 8601 datetime)*
  - `end_date` *(optional ISO 8601 datetime)*
- **Example Response Data:**
  ```json
  {
    "total_incidents": 15,
    "resolved_incidents": 7,
    "open_incidents": 8,
    "resolution_rate_pct": 46.67,
    "target_met": false,
    "avg_time_to_resolve_hrs": 6.71,
    "avg_time_to_review_hrs": 2.7,
    "by_severity": { "low": 2, "medium": 4, "high": 5, "critical": 4 },
    "by_type": { "ppe_violation": 6, "restricted_zone_intrusion": 3, "potential_fatigue": 4, "fall": 2 }
  }
  ```

#### 4. `GET /api/v1/analytics/productivity`
- **Purpose:** Throughput per worker and classification of high/low performers.
- **Query Parameters:**
  - `factory_id` *(optional UUID)*
  - `start_date` *(optional ISO 8601 datetime)*
  - `end_date` *(optional ISO 8601 datetime)*
  - `low_threshold` *(optional int, default 2)*
  - `high_threshold` *(optional int, default 5)*
- **Validation:** `low_threshold` must not exceed `high_threshold`.
- **Example Response Data:**
  ```json
  {
    "total_incidents_handled": 17,
    "workers_analysed": 7,
    "avg_handled_per_worker": 2.43,
    "per_worker": [
      {
        "full_name": "Seif Sameh",
        "role": "factory_manager",
        "incidents_reviewed": 0,
        "incidents_resolved": 4,
        "total_handled": 4,
        "productivity_label": "normal"
      }
    ],
    "low_performers": ["Khaled Ibrahim", "Mahmoud Ali", "Abdallah Waleed"],
    "high_performers": []
  }
  ```

#### 5. `GET /api/v1/analytics/camera-coverage`
- **Purpose:** Camera stream uptime and outage gap tracking.
- **Query Parameters:**
  - `factory_id` *(optional UUID)*
  - `period_hours` *(optional float > 0, default 720.0 = 30 days)*
- **Example Response Data:**
  ```json
  {
    "total_cameras": 4,
    "active_cameras": 3,
    "inactive_cameras": 1,
    "total_downtime_hrs": 4.0,
    "overall_coverage_pct": 99.81,
    "per_camera": [
      {
        "camera_name": "Welding-CAM-01",
        "department_name": "Welding Zone",
        "is_active": true,
        "total_downtime_hrs": 2.0,
        "gap_count": 1
      }
    ]
  }
  ```

#### 6. `GET /api/v1/analytics/summary`
- **Purpose:** Combines all 5 metrics into a single response.

---

## 5. Instructions for Seif (FastAPI Backend Integration)

Seif does **NOT** need to write SQL or analytics logic. Simply import `WorkforceAnalyticsService` and register the router.

### Complete FastAPI Router Example

```python
# app/routers/analytics.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException

from workforce_analytics.services.analytics_service import WorkforceAnalyticsService
from workforce_analytics.api_contracts.requests import (
    AttendanceQueryRequest,
    CameraCoverageQueryRequest,
    IncidentQueryRequest,
    ProductivityQueryRequest,
    SummaryQueryRequest,
    WorkforceQueryRequest,
)
from workforce_analytics.api_contracts.responses import (
    AttendanceResponse,
    CameraCoverageResponse,
    IncidentAnalyticsResponse,
    ProductivityResponse,
    WorkforceOverviewResponse,
    WorkforceSummaryResponse,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Workforce Analytics"])

def get_service() -> WorkforceAnalyticsService:
    return WorkforceAnalyticsService()

@router.get("/workforce", response_model=WorkforceOverviewResponse)
def get_workforce_overview(
    factory_id: Optional[UUID] = Query(None),
    service: WorkforceAnalyticsService = Depends(get_service),
):
    data = service.get_workforce_overview(factory_id=factory_id)
    return {"status": "success", "data": data}

@router.get("/attendance", response_model=AttendanceResponse)
def get_attendance(
    factory_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    service: WorkforceAnalyticsService = Depends(get_service),
):
    try:
        req = AttendanceQueryRequest(factory_id=factory_id, start_date=start_date, end_date=end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data = service.get_attendance_metrics(factory_id=req.factory_id, start_date=req.start_date, end_date=req.end_date)
    return {"status": "success", "data": data}

@router.get("/incidents", response_model=IncidentAnalyticsResponse)
def get_incidents(
    factory_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    service: WorkforceAnalyticsService = Depends(get_service),
):
    try:
        req = IncidentQueryRequest(factory_id=factory_id, start_date=start_date, end_date=end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data = service.get_incident_analytics(factory_id=req.factory_id, start_date=req.start_date, end_date=req.end_date)
    return {"status": "success", "data": data}

@router.get("/productivity", response_model=ProductivityResponse)
def get_productivity(
    factory_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    low_threshold: Optional[int] = Query(None, ge=0),
    high_threshold: Optional[int] = Query(None, ge=0),
    service: WorkforceAnalyticsService = Depends(get_service),
):
    try:
        req = ProductivityQueryRequest(
            factory_id=factory_id, start_date=start_date, end_date=end_date,
            low_threshold=low_threshold, high_threshold=high_threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data = service.get_productivity_metrics(
        factory_id=req.factory_id, start_date=req.start_date, end_date=req.end_date,
        low_threshold=req.low_threshold, high_threshold=req.high_threshold,
    )
    return {"status": "success", "data": data}

@router.get("/camera-coverage", response_model=CameraCoverageResponse)
def get_camera_coverage(
    factory_id: Optional[UUID] = Query(None),
    period_hours: float = Query(720.0, gt=0),
    service: WorkforceAnalyticsService = Depends(get_service),
):
    data = service.get_camera_coverage(factory_id=factory_id, period_hours=period_hours)
    return {"status": "success", "data": data}

@router.get("/summary", response_model=WorkforceSummaryResponse)
def get_summary(
    factory_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    period_hours: float = Query(720.0, gt=0),
    service: WorkforceAnalyticsService = Depends(get_service),
):
    try:
        req = SummaryQueryRequest(factory_id=factory_id, start_date=start_date, end_date=end_date, period_hours=period_hours)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    data = service.get_workforce_summary(
        factory_id=req.factory_id, start_date=req.start_date, end_date=req.end_date, period_hours=req.period_hours,
    )
    return {"status": "success", "data": data}
```

---

## 6. Instructions for Taqi (Frontend Dashboard Consumption)

Taqi can consume these endpoints from vanilla JavaScript:

```javascript
// Example: Fetch and Render Workforce Summary in Dashboard
async function loadWorkforceDashboard() {
  const API_BASE = "http://localhost:8000/api/v1/analytics";

  try {
    const response = await fetch(`${API_BASE}/summary`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    const data = result.data;

    // Update Overview Cards
    document.getElementById("active-workers-count").textContent = data.overview.active_workers;
    document.getElementById("attendance-rate").textContent = `${data.attendance.activity_rate_pct}%`;
    document.getElementById("incident-resolution-rate").textContent = `${data.incidents.resolution_rate_pct}%`;
    document.getElementById("camera-coverage-pct").textContent = `${data.camera_coverage.overall_coverage_pct}%`;

    // Render Productivity Table
    renderProductivityTable(data.productivity.per_worker);

  } catch (error) {
    console.error("Failed to load workforce analytics:", error);
  }
}
```

---

## 7. Windows PowerShell Commands

Execute all commands from the `backend/ai-services` folder:

```powershell
cd "d:\Menoufia National University 2026-2027\Faculty_of_Computers_&_Artificial_Intelligence\Level 4\Graduated Project 2026-2027\Operix\backend\ai-services"

# 1. Run the live Analytics Demo
python run_demo.py

# 2. Run the Service Integration Demo
python integration/analytics_demo.py

# 3. Run all 64 Automated Tests (Zero External Dependencies)
python run_tests.py
```

All 64 tests are guaranteed to run and pass against the live `operix_db` PostgreSQL database.
