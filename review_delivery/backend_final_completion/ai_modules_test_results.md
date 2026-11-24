# AI Modules Test Results (`TEST_MODE=1`, `APP_ENV=test`)

| Suite | Command | Passed | Failed | Skipped | Deselected / Blocked |
|---|---|---:|---:|---:|---|
| Incident Evidence | `pytest incident_evidence/tests/ -q` | 53 | 0 | 0 | 0 |
| Reports Generation | `pytest reports_generation/tests/ -q` | 73 | 0 | 0 | 0 |
| Workforce Analytics | `pytest workforce_analytics/tests/ -q` | 25 | 0 | 51 | 51 DB-dependent skipped |
| RAG Security & Assistant | `pytest llm_rag_assistant/tests/test_assistant.py llm_rag_assistant/tests/test_agentic_actions.py llm_rag_assistant/tests/test_phase3_4_security.py -q` | 21 | 0 | 0 | 0 |
| RAG End-to-End | `pytest llm_rag_assistant/tests/test_end_to_end.py -k "not test_e2e_ingestion_counts" -q` | 8 | 1 | 0 | 1 deselected (`test_e2e_ingestion_counts`); `test_e2e_benchmark_evaluator` 62.5% < 75% offline (missing DB chunks for BENCH-04/07/08) |
