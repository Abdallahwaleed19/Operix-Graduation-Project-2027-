# Backend Test Results

**Environment:** `TEST_MODE=1`, `APP_ENV=test`, `redis==8.2.0` installed, `conftest.py` SQLite (`sqlite:///./test_operix.db`) with `OPERIX_REJECT_PRODUCTION_DB=1`.

1. **AI Router Contract Suite (`pytest tests/test_phase42_ai_routers.py -v`):**
   - **Result:** **26 passed, 0 failed, 0 skipped** (`2.32s`).
   - Includes `TestAnalyticsRouter` (6), `TestAssistantRouter` (7, including Seif's `cdda98c` `clear_conversation` + 403 tests), `TestReportsRouter` (5, including `test_get_and_download_report_strict_signature_contract`), and `TestEvidenceRouter` (8).

2. **All Phase 4 Backend Suites (`pytest tests/test_phase41_ai_deps.py tests/test_phase42_ai_routers.py tests/test_phase43_ai_actions.py tests/test_phase4_remediation.py -q`):**
   - **Result:** **74 passed, 0 failed, 0 skipped** (`2.72s`).

3. **Full Backend Offline Suite (`pytest tests/ -q`):**
   - **Result:** **177 passed, 5 deselected, 26 errors** (`19.45s`).
   - **Root Cause of 26 Errors:** `sqlalchemy.exc.CompileError` in `test_event_incident_integration.py` (5), `test_rule_evaluation.py` (13), and `test_rules.py` (8) when compiling PostgreSQL-specific column types on SQLite (`conftest.py`). All 74 Phase 4 AI Backend tests passed.
