# Workforce Analytics API

**Router File:** `backend/app/api/v1/endpoints/analytics.py`  
**Router Prefix:** `/api/v1/analytics`  
**Auth & DB:** All endpoints require `Depends(get_current_user_context)` and `Depends(get_tenant_db)`. `factory_id` is scoped automatically from `user.factory_id`.

---

## Endpoints (All `200 OK`, Implemented & Registered)

| Method & Path | Query Parameters | Description |
|---|---|---|
| `GET /api/v1/analytics/overview` | None | Total workers, active/inactive split, role distribution |
| `GET /api/v1/analytics/attendance` | `start_date` (datetime, opt), `end_date` (datetime, opt) | Attendance & activity proxy metrics |
| `GET /api/v1/analytics/incidents` | `start_date` (datetime, opt), `end_date` (datetime, opt) | Incident counts, resolution rates, severity/state/type distributions |
| `GET /api/v1/analytics/productivity` | `start_date`, `end_date`, `low_threshold` (int >= 0), `high_threshold` (int >= 0) | Per-worker incident resolution metrics |
| `GET /api/v1/analytics/camera-coverage` | `period_hours` (float 1.0..8760.0, default `720.0`) | Camera uptime % and downtime gaps |
| `GET /api/v1/analytics/summary` | `start_date`, `end_date`, `period_hours` (default `720.0`) | Consolidated dashboard summary card payload |

---

## Example Response (`GET /api/v1/analytics/overview`)
```json
{
  "status": "success",
  "data": {
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "total_workers": 24,
    "active_workers": 22,
    "inactive_workers": 2,
    "role_breakdown": {
      "operator": 18,
      "safety_supervisor": 4,
      "factory_manager": 2
    }
  },
  "meta": {
    "request_timestamp": "2026-11-24T19:50:00Z",
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "api_version": "v1"
  }
}
```

## JavaScript Fetch Example
```javascript
const params = new URLSearchParams({ period_hours: "720" });
const res = await fetch(`${API_BASE_URL}/api/v1/analytics/summary?${params}`, {
  headers: { "Authorization": `Bearer ${token}` },
});
const json = await res.json();
```
**React Note:** Pass ISO-8601 UTC strings (e.g., `new Date().toISOString()`) for `start_date` and `end_date`.
