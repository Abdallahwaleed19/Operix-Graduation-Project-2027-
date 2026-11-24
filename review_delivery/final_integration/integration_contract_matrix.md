# Integration Contract Matrix

| Module | Backend Dependency | AI Service Target | Contract Match? | Notes |
|---|---|---|---|---|
| Evidence | `get_evidence_service_dep` | `EvidenceService` (`conn=db`, `factory_id=user.factory_id`) | Yes | All 5 endpoints aligned |
| Workforce | `get_workforce_analytics_service_dep` | `WorkforceAnalyticsService` (`session=db`, `factory_id=user.factory_id`) | Yes | All 6 endpoints aligned |
| Assistant (`ask`, `sources`, `health`) | `get_llm_assistant_service_dep` | `OperixAssistantService` (`UserContext` from `AuthenticatedUser`) | Yes | Server overwrites client `user_context` |
| Assistant (`clear_conversation`) | `assistant.py:165` | `clear_conversation(id, factory_id, user_id)` | Pending Approval | Local fix in `assistant.py` awaits Seif sign-off |
| AI Actions | `get_ai_action_service` | `AIActionService.execute_action(...)` | Yes | `SUPPORTED_ACTION_TYPES` & RBAC aligned |
| Reports (`generate`, `list`) | `get_reports_service_dep` | `ReportService.generate_report`, `list_reports` | Yes | Both pass `factory_id=user.factory_id` |
| Reports (`get`, `download`) | `reports.py:110,136,142` | `get_report(id, factory_id)`, `get_report_file_path(id, factory_id)` | **NO (Blocker)** | `reports.py` omits `factory_id` -> runtime `TypeError` |
