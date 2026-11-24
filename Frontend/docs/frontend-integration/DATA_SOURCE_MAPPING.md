# Frontend Data Source Mapping

| Page / Component | Route | Service | Data Source | Status |
| :--- | :--- | :--- | :--- | :--- |
| `FactoryOverviewPage` | `/`, `/dashboard` | `analyticsService` | PostgreSQL via `/api/v1/analytics/overview`, `/summary` | **Live API** |
| `WorkforceAnalyticsPage` | `/analytics` | `analyticsService` | PostgreSQL via `/api/v1/analytics/*` | **Live API** |
| `AIAssistantPage` | `/assistant` | `assistantService` | FastAPI RAG + Actions (`/api/v1/assistant/*`) | **Live API** |
| `ReportsPage` | `/reports` | `reportService` | PostgreSQL + File Storage (`/api/v1/reports/*`) | **Live API** |
| `RuleBuilderPage` & `EditRulePage` | `/rules`, `/rules/edit/:id` | `ruleService` | PostgreSQL `SafetyRule` (`/api/v1/rules/*`) | **Live API** |
| `IncidentsPage` (Evidence Modal) | `/incidents` | `incidentService` | PostgreSQL `EvidenceFile` (`/api/v1/evidence/*`) | **Live API** |
| `AppLayout` (Real-Time Stream) | `*` (Authenticated) | `websocketService` | Redis + FastAPI WS (`/ws/v2/events`) | **Live WS** |
| `LoginPage`, `RegisterPage`, `ProfilePage` | `/login`, `/profile` | `authService` | UI Preview (`isMockEnabled('auth') = true`) | **Pending S-1** |
| `IncidentsPage` (Table & Resolve) | `/incidents` | `incidentService` | UI Preview (`isMockEnabled('incidents') = true`) | **Pending S-2** |
| `CamerasPage`, `SensorsPage`, `LiveMonitoringPage`, `ThermalMonitoringPage` | `/monitoring`, `/thermal`, `/settings/cameras`, `/settings/sensors` | `cameraService`, `sensorService` | UI Preview (`isMockEnabled('cameras'/'sensors') = true`) | **Pending S-3** |
| `UsersRolesPage`, `FactorySettingsPage`, `RoleMatrixPage` | `/settings/users`, `/settings/factory`, `/settings/roles` | `userService`, `factoryService` | UI Preview (`isMockEnabled('users'/'factory') = true`) | **Pending S-4** |
| `HeatmapsTrackingPage` | `/heatmaps` | *None* | Redirects to `/analytics` | **Removed** |
