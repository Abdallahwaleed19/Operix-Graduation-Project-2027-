# Incident Evidence API

**Router File:** `backend/app/api/v1/endpoints/evidence.py`  
**Router Prefix:** `/api/v1/evidence`  
**Auth & DB:** All endpoints require `Depends(get_current_user_context)` and `Depends(get_tenant_db)`.

---

## 1. Upload Incident Evidence
- **Endpoint:** `POST /api/v1/evidence/upload`
- **Status:** Implemented and registered (`201 Created`)
- **Request Body (`EvidenceUploadJsonIn`):**
  - `event_id` (UUID, required)
  - `kind` (string, default `"snapshot"` — `"snapshot"` or `"clip"`)
  - `file_base64` (string, required — Base64-encoded bytes)
  - `content_type` (string, default `"image/jpeg"`, e.g., `"image/jpeg"`, `"video/mp4"`)
  - `duration_s` (float, optional — required when `kind === "clip"`)
  - `captured_at` (ISO-8601 datetime, optional — defaults to UTC now)

```json
{
  "event_id": "11111111-1111-1111-1111-111111111111",
  "kind": "snapshot",
  "file_base64": "/9j/4AAQSkZJRgABAQ...",
  "content_type": "image/jpeg"
}
```
- **Errors:** `400 INVALID_BASE64`, `400 INVALID_EVIDENCE_PAYLOAD`, `401`, `403`, `422 VALIDATION_ERROR`.

---

## 2. List Evidence Records
- **Endpoint:** `GET /api/v1/evidence`
- **Status:** Implemented and registered (`200 OK`)
- **Query Parameters:** `event_id` (UUID, optional), `incident_id` (UUID, optional), `kind` (`"snapshot"` | `"clip"`, optional), `page` (int >= 1, default `1`), `page_size` (int 1..100, default `20`).

---

## 3. Get Evidence Metadata
- **Endpoint:** `GET /api/v1/evidence/{evidence_id}`
- **Status:** Implemented and registered (`200 OK`)
- **Path Parameter:** `evidence_id` (UUID)

---

## 4. Download Evidence File
- **Endpoint:** `GET /api/v1/evidence/{evidence_id}/download`
- **Status:** Implemented and registered (`200 OK`)
- **Response:** Raw binary bytes with `Content-Type` and `Content-Disposition: attachment; filename="..."`.

---

## 5. Verify Evidence Integrity
- **Endpoint:** `POST /api/v1/evidence/{evidence_id}/verify-integrity`
- **Status:** Implemented and registered (`200 OK`)
- **Description:** Recomputes SHA-256 hash on disk and compares with stored database checksum.

---

## JavaScript Fetch Example (Upload)
```javascript
const res = await fetch(`${API_BASE_URL}/api/v1/evidence/upload`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    event_id: eventId,
    kind: "snapshot",
    file_base64: base64String,
    content_type: "image/jpeg",
  }),
});
```
**React Note:** Convert `<input type="file">` with `FileReader.readAsDataURL()` and strip the `data:...;base64,` prefix before sending `file_base64`.
