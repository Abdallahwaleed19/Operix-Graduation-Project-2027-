# Operix Integration Status

**Last Updated:** 2026-11-25  
**Frontend Dual-Mode:** `VITE_USE_MOCK_DATA=false` (Connected Modules Live)

---

## 1. Connected Modules (Live FastAPI + PostgreSQL)

| Module | Frontend Service | Backend Router | Status |
| :--- | :--- | :--- | :--- |
| **A. Analytics** | `analyticsService.js` | `/api/v1/analytics/*` (6 endpoints) | **Connected** |
| **B. AI Assistant & Actions** | `assistantService.js` | `/api/v1/assistant/*` (5 endpoints) | **Connected** |
| **C. Reports** | `reportService.js` | `/api/v1/reports/*` (4 endpoints) | **Connected** |
| **D. Incident Evidence** | `incidentService.js` | `/api/v1/evidence/*` (5 endpoints) | **Connected** |
| **E. Safety Rules** | `ruleService.js` | `/api/v1/rules/*` (6 endpoints) | **Connected** |
| **F. Real-Time WebSockets** | `websocketService.js` | `/ws/v2/events` + `/api/v1/auth/ws-ticket` | **Connected** |

---

## 2. Pending Backend Dependencies (UI-Only Preparation)

| Module | Frontend Pages & Services | Missing Backend Endpoints | Owner |
| :--- | :--- | :--- | :--- |
| **S-1: Core Auth & Profile** | `LoginPage`, `RegisterPage`, `ProfilePage`, `authService.js` | `/auth/login`, `/auth/register`, `/auth/me`, `/auth/refresh` | Seif |
| **S-2: Incidents CRUD** | `IncidentsPage` (list, resolve), `incidentService.js` | `GET /incidents`, `POST /incidents/{id}/resolve` | Seif |
| **S-3: Cameras & Sensors** | `CamerasPage`, `SensorsPage`, `LiveMonitoringPage`, `ThermalMonitoringPage` | `/api/v1/cameras/*`, `/api/v1/sensors/*` | Seif |
| **S-4: Users, Roles & Factory** | `UsersRolesPage`, `FactorySettingsPage`, `RoleMatrixPage` | `/api/v1/users/*`, `/api/v1/roles/*`, `/api/v1/factory/*` | Seif |

---

## 3. Removed Features

| Feature | Status | Action Taken |
| :--- | :--- | :--- |
| **Heatmaps & Tracking** | **Removed** | Removed from `Sidebar.jsx`; `/heatmaps` redirects to `/analytics`; `HeatmapsTrackingPage.jsx` deprecated. |
