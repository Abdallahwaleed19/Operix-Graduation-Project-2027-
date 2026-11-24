# Test Results Summary (`TEST_MODE=1`, `APP_ENV=test`)

| Suite | Command | Passed | Failed | Skipped | Blocked / Not Run | Notes |
|---|---|---:|---:|---:|---:|---|
| Incident Evidence | `pytest incident_evidence/tests/ -q` | 53 | 0 | 0 | 0 | All unit & security tests pass |
| Workforce Analytics | `pytest workforce_analytics/tests/ -q` | 25 | 0 | 51 | 0 | DB-dependent tests skipped offline |
| RAG Security & Assistant | `pytest llm_rag_assistant/tests/test_assistant.py llm_rag_assistant/tests/test_agentic_actions.py llm_rag_assistant/tests/test_phase3_4_security.py -v` | 21 | 0 | 0 | 0 | Mock LLM/Embedding |
| RAG End-to-End | `pytest llm_rag_assistant/tests/test_end_to_end.py -k "not test_e2e_ingestion_counts" -v` | 8 | 1 | 0 | 1 | `test_e2e_benchmark_evaluator` 62.5% < 75% (BENCH-04/07/08 missing DB chunks); `test_e2e_ingestion_counts` deselected |
| Reports Generation | `pytest reports_generation/tests/ -v` | 73 | 0 | 0 | 0 | Includes `sqlite:///:memory:` `engine=` lifecycle test |
| Backend Tests (`backend/tests/`) | Not run | 0 | 0 | 0 | All | Blocked: `ModuleNotFoundError: No module named 'redis'` |
