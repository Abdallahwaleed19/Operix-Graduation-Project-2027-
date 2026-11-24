# AI Modules Integration Report

| Module | Status | Summary |
|---|---|---|
| **Incident Evidence** | **Fully Integrated** | Uses canonical `EvidenceFile`, injected `Session`, `get_evidence_storage_dir()`, hardened `_safe_resolve()`. Registered in `evidence.py` (5 endpoints). |
| **Workforce Analytics** | **Fully Integrated** | Uses canonical `app.models`, injected `Session`, production `DEFAULT_FACTORY_ID` guard (`EnvironmentError` if unset in prod). Registered in `analytics.py` (6 endpoints). |
| **AI Actions** | **Fully Integrated** | `OperixActionService` delegates to canonical `AIActionService.execute_action()`; `SUPPORTED_ACTION_TYPES` and `PRIVILEGED_ACTION_TYPES` aligned. Registered at `POST /api/v1/assistant/actions/execute`. |
| **RAG Assistant** | **Partially Integrated** | `ask`, `sources`, `health` integrated with `UserContext` & `ConversationOwnershipError`. `DELETE /conversations/{id}` in `assistant.py` has a pending local fix awaiting Seif's approval. |
| **Reports Generation** | **Partially Integrated** | `generate` & `list_reports` integrated; `ReportService` & `ReportRepository` hardened (`engine=` & `session=`). **Blocker:** `reports.py` (lines 110, 136, 142) omits `factory_id` when calling `get_report()` / `get_report_file_path()`. |
