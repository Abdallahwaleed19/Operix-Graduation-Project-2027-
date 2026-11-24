# Reports Generation API

**Router File:** `backend/app/api/v1/endpoints/reports.py`  
**Router Prefix:** `/api/v1/reports`  
**Auth:** All endpoints require `Depends(get_current_user_context)`.

---

## 1. Generate Safety Report
- **Endpoint:** `POST /api/v1/reports/generate`
- **Status:** Implemented and registered (`201 Created`)
- **Request Body (`ReportGenerateIn`):**
  - `report_type` (`"workforce"` | `"incident"` | `"camera_coverage"` | `"comprehensive_safety"`, required)
  - `format` (`"pdf"` | `"excel"`, default `"pdf"`)
  - `date_from` (YYYY-MM-DD, optional)
  - `date_to` (YYYY-MM-DD, optional)

```json
{
  "report_type": "workforce",
  "format": "pdf",
  "date_from": "2026-11-01",
  "date_to": "2026-11-24"
}
```

---

## 2. List Generated Reports
- **Endpoint:** `GET /api/v1/reports`
- **Status:** Implemented and registered (`200 OK`)
- **Behavior:** Returns `APIResponse[List[Dict]]` scoped to `user.factory_id`.

---

## 3. Get Report Metadata
- **Endpoint:** `GET /api/v1/reports/{report_id}`
- **Status:** Implemented and registered (`200 OK`, `reports.py:110` passes `factory_id=user.factory_id` per Seif commit `cdda98c`).

---

## 4. Download Report Artifact
- **Endpoint:** `GET /api/v1/reports/{report_id}/download`
- **Status:** Implemented and registered (`200 OK`, `reports.py:136,142` pass `factory_id=user.factory_id` per Seif commit `cdda98c`; returns PDF/Excel binary stream).

---

## JavaScript Example (Generate & List)
```javascript
const res = await fetch(`${API_BASE_URL}/api/v1/reports/generate`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ report_type: "workforce", format: "pdf" }),
});
```
