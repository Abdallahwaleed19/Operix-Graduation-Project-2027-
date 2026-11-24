# Integration Test Results

- **AI-Module Isolated Integration Workflows:**
  - **Evidence:** Upload, metadata, download, integrity, path traversal, and factory isolation verified in unit/security tests (53 passed).
  - **Workforce:** Service facade, canonical model re-exports, session injection, and production factory guard verified (25 passed, 51 DB-skipped).
  - **RAG:** `UserContext` enforcement, `ConversationOwnershipError` (cross-user & cross-factory), and `RAGEvaluator` verified (21 security/assistant + 8 E2E passed; `test_e2e_benchmark_evaluator` blocked offline at 62.5%).
  - **Reports:** `ReportService` factory isolation & `ReportRepository(engine=...)` `sqlite:///:memory:` lifecycle verified (73 passed).
  - **AI Actions:** Delegation to `AIActionService.execute_action()` verified via `AsyncMock` in `test_phase3_4_security.py`.
- **Full FastAPI HTTP Integration (`backend/tests/test_phase4*.py`):** **BLOCKED** by missing `redis` package in Python 3.14 environment and offline `operix_db` policy.
- **Reports Download HTTP Endpoint:** **BLOCKED** by missing `factory_id` argument in `backend/app/api/v1/endpoints/reports.py` (lines 110, 136, 142).
