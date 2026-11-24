# Backend Test Results (Final)

**Environment:** `TEST_MODE=1`, `APP_ENV=test`, `redis==8.2.0` installed, `conftest.py` SQLite (`sqlite:///./test_operix.db`) with `@compiles(CITEXT, "sqlite")` and `@compiles(JSONB, "sqlite")` test-only adapters.

| Suite | Command | Before | After |
|---|---|---|---:|
| AI Router Contracts | `pytest tests/test_phase42_ai_routers.py -v` | 26 passed | **26 passed** (`2.32s`) |
| All Phase 4 Backend Suites | `pytest tests/test_phase41_ai_deps.py tests/test_phase42_ai_routers.py tests/test_phase43_ai_actions.py tests/test_phase4_remediation.py -q` | 74 passed | **74 passed** (`2.72s`) |
| Previously Failing Dialect Tests | `pytest tests/test_rules.py tests/test_rule_evaluation.py tests/test_event_incident_integration.py -q` | 26 errors (`CompileError` on `JSONB`) | **26 passed** (`1.34s`) |
| Full Backend Offline Suite | `pytest tests/ -q` | 177 passed, 5 deselected, 26 errors | **203 passed, 5 deselected, 0 errors** (`20.30s`) |
