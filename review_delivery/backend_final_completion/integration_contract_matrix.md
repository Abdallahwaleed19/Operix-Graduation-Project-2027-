# Integration Contract Matrix

| Endpoint / Service | Caller (`backend/app/`) | Callee (`backend/ai-services/`) | Status |
|---|---|---|---|
| `POST /api/v1/evidence/upload` .. `verify-integrity` | `evidence.py` (`user.factory_id`, `db`) | `EvidenceService` | **Verified Match** |
| `GET /api/v1/analytics/*` (6 routes) | `analytics.py` (`user.factory_id`, `db`) | `WorkforceAnalyticsService` | **Verified Match** |
| `POST /api/v1/assistant/ask` | `assistant.py` (`UserContext` from `AuthenticatedUser`) | `OperixAssistantService.ask()` | **Verified Match** |
| `DELETE /api/v1/assistant/conversations/{id}` | `assistant.py:167` (`factory_id`, `user_id`, `PermissionError` -> 403) | `OperixAssistantService.clear_conversation()` | **Verified Match (`cdda98c`)** |
| `POST /api/v1/assistant/actions/execute` | `assistant.py:103` | `AIActionService.execute_action()` | **Verified Match** |
| `POST /api/v1/reports/generate`, `GET /api/v1/reports` | `reports.py:61,88` (`factory_id=user.factory_id`) | `ReportService` | **Verified Match** |
| `GET /api/v1/reports/{id}`, `/download` | `reports.py:110,136,142` (`factory_id=user.factory_id`) | `ReportService.get_report`, `get_report_file_path` | **Verified Match (`cdda98c`)** |
