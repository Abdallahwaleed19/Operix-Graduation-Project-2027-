# Pending Backend Dependencies (S-1 through S-4)

These modules have complete UI preparation in the Frontend (`PendingBackendBadge` displayed cleanly) and isolated service interfaces, but **must not** be switched to live API mode until the Core Backend endpoints are implemented by Seif.

---

## S-1: Core Authentication & User Profile
- **Frontend:** `LoginPage.jsx`, `RegisterPage.jsx`, `ForgotPasswordPage.jsx`, `ProfilePage.jsx`, `authService.js`
- **Dual-Mode Flag:** `isMockEnabled('auth')` defaults to `true`
- **Missing Backend Endpoints:**
  - `POST /api/v1/auth/login` (currently only `/api/v1/auth/ws-ticket` exists in `auth.py`)
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/refresh`
  - `GET /api/v1/auth/me` & `PATCH /api/v1/auth/me`

## S-2: Incidents CRUD & Resolution
- **Frontend:** `IncidentsPage.jsx` (table, filters, resolve button), `incidentService.js`
- **Dual-Mode Flag:** `isMockEnabled('incidents')` defaults to `true` *(Note: Evidence Drawer inside `IncidentsPage` is **Live** via `/api/v1/evidence/*`)*
- **Missing Backend Endpoints:**
  - `GET /api/v1/incidents`
  - `GET /api/v1/incidents/{incident_id}`
  - `POST /api/v1/incidents/{incident_id}/resolve`

## S-3: Cameras & Sensors Management
- **Frontend:** `CamerasPage.jsx`, `EditCameraPage.jsx`, `SensorsPage.jsx`, `EditSensorPage.jsx`, `LiveMonitoringPage.jsx`, `ThermalMonitoringPage.jsx`, `cameraService.js`, `sensorService.js`
- **Dual-Mode Flag:** `isMockEnabled('cameras')` and `isMockEnabled('sensors')` default to `true`
- **Missing Backend Endpoints:**
  - `GET/POST/PUT/DELETE /api/v1/cameras`
  - `GET/POST/PUT/DELETE /api/v1/sensors`

## S-4: Users, Roles & Factory Settings
- **Frontend:** `UsersRolesPage.jsx`, `FactorySettingsPage.jsx`, `RoleMatrixPage.jsx`, `userService.js`, `factoryService.js`
- **Dual-Mode Flag:** `isMockEnabled('users')` and `isMockEnabled('factory')` default to `true`
- **Missing Backend Endpoints:**
  - `GET/POST/PATCH /api/v1/users`
  - `GET/PUT /api/v1/roles`
  - `GET/PUT /api/v1/factory/settings`
