# Operix Phase 5 — Operational & Authentication APIs (For Toka)

**Base Prefix:** `/api/v1` (default local URL `http://localhost:8000`)
**Standard Headers:** `Authorization: Bearer <access_token>` and `X-Factory-Id: <factory_uuid>` (required on all tenant-scoped endpoints except `/auth/login`, `/auth/refresh`, `/auth/logout`).
**Standard Envelope:**
- Success: `{ "status": "success", "data": <T>, "meta": { "factory_id": "<uuid>", ... } }`
- Error: `{ "status": "error", "error_code": "<CODE>", "message": "...", "details": ... }`

---

## 1. S-1 Authentication (`/api/v1/auth`)

| Method | Path | Auth | RBAC | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Public | Active User + Membership | Authenticate with `{ email, password, factory_id? }` → `{ access_token, refresh_token, token_type, expires_in, user }` |
| `GET` | `/api/v1/auth/me` | Bearer + `X-Factory-Id` | Any active member | Returns `{ user_id, factory_id, role, full_name, email }` |
| `POST` | `/api/v1/auth/refresh` | Public | Active User + Refresh Token | Rotates `{ refresh_token, factory_id? }` → fresh `{ access_token, refresh_token, ... }` |
| `POST` | `/api/v1/auth/logout` | Public | None | Revokes `{ refresh_token }` → `{ revoked: boolean }` |
| `POST` | `/api/v1/auth/ws-ticket` | Bearer | Active member | Existing one-time WS ticket issuance for `/ws/v2/events` |

```js
// Example Login + Me
const loginRes = await fetch("http://localhost:8000/api/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "mona@plant1.example", password: "..." }),
});
```

---

## 2. S-2 Incidents Management (`/api/v1/incidents`)

| Method | Path | Auth | RBAC | Query / Body |
|---|---|---|---|---|
| `GET` | `/api/v1/incidents` | Bearer + `X-Factory-Id` | Any active member | Query: `state`, `severity`, `incident_type`, `limit`, `offset` |
| `GET` | `/api/v1/incidents/{incident_id}` | Bearer + `X-Factory-Id` | Any active member | Path: `incident_id` (UUID) |
| `POST` | `/api/v1/incidents` | Bearer + `X-Factory-Id` | `safety_supervisor`, `factory_manager`, `factory_admin` | Body: `{ incident_type, severity }` |
| `PATCH` | `/api/v1/incidents/{incident_id}` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Body: `{ severity?, resolution_note? }` |
| `PATCH` | `/api/v1/incidents/{incident_id}/acknowledge` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Transitions to `under_review` + WS broadcast |
| `PATCH` | `/api/v1/incidents/{incident_id}/resolve` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Body (optional): `{ resolution_note? }` → `resolved` + WS broadcast |

---

## 3. S-3 Cameras & Sensors (`/api/v1/devices`)

| Method | Path | Auth | RBAC | Notes |
|---|---|---|---|---|
| `GET` | `/api/v1/devices/cameras` | Bearer + `X-Factory-Id` | Any active member | Query: `status`, `is_active`, `department_id`, `limit`, `offset` |
| `GET` | `/api/v1/devices/cameras/{camera_id}` | Bearer + `X-Factory-Id` | Any active member | Tenant-isolated camera details |
| `POST` | `/api/v1/devices/cameras` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Body: `{ name, camera_type, department_id?, location_label?, stream_url_ref, is_active? }` |
| `PATCH` | `/api/v1/devices/cameras/{camera_id}` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Partial camera config update |
| `POST` | `/api/v1/devices/cameras/{camera_id}/toggle` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Toggles `is_active` and `status` |
| `GET` | `/api/v1/devices/sensors` | Bearer + `X-Factory-Id` | Any active member | Excludes `device_key_hash` |
| `GET` | `/api/v1/devices/sensors/{sensor_id}` | Bearer + `X-Factory-Id` | Any active member | Excludes `device_key_hash` |
| `POST` | `/api/v1/devices/sensors` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Body: `{ name, sensor_type?, unit?, department_id?, location_label?, sampling_interval_s?, is_active? }` |
| `PATCH` | `/api/v1/devices/sensors/{sensor_id}` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Partial sensor config update |
| `POST` | `/api/v1/devices/sensors/{sensor_id}/toggle` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Toggles `is_active` and `status` |
| `GET` | `/api/v1/devices/sensors/{sensor_id}/readings` | Bearer + `X-Factory-Id` | Any active member | Query: `limit`, `offset` |

---

## 4. S-4 Users, Roles & Factory Settings (`/api/v1/users`, `/roles`, `/factories`)

| Method | Path | Auth | RBAC | Notes |
|---|---|---|---|---|
| `GET` | `/api/v1/users` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Excludes `password_hash`, token hashes, lockout metadata |
| `GET` | `/api/v1/users/{user_id}` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Scoped to current factory |
| `POST` | `/api/v1/users/invite` | Bearer + `X-Factory-Id` | Manager / Admin | Body: `{ email, full_name, role_code }` |
| `PATCH` | `/api/v1/users/{user_id}` | Bearer + `X-Factory-Id` | Manager / Admin | Body: `{ full_name?, status?, membership_active?, role_code? }` |
| `GET` | `/api/v1/roles` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Returns canonical roles + mapped permissions |
| `GET` | `/api/v1/roles/permissions` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Returns canonical permissions |
| `GET` | `/api/v1/roles/{role_id}` | Bearer + `X-Factory-Id` | Supervisor / Manager / Admin | Role details + permissions |
| `PATCH` | `/api/v1/roles/memberships/{user_id}` | Bearer + `X-Factory-Id` | Manager / Admin | Body: `{ role_code }` |
| `GET` | `/api/v1/factories/current` | Bearer + `X-Factory-Id` | Any active member | Returns `{ id, name, slug, status, timezone, evidence_retention_days, created_at, updated_at }` |
| `PATCH` | `/api/v1/factories/current` | Bearer + `X-Factory-Id` | Manager / Admin | Body: `{ name?, timezone?, evidence_retention_days? }` |
