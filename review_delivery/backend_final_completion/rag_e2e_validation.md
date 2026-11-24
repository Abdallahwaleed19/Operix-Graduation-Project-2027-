# RAG E2E Validation Report

- **Command:** `pytest llm_rag_assistant/tests/test_end_to_end.py -k "not test_e2e_ingestion_counts" -q` (`TEST_MODE=1`, `APP_ENV=test`, `LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`)
- **Result:** `8 passed, 1 failed, 1 deselected`
- **Passing Tests (8):** `test_e2e_query_safety_rule`, `test_e2e_query_incident`, `test_e2e_unknown_query_honest_refusal`, `test_e2e_evaluator_requires_explicit_user_context`, `test_e2e_owner_can_access_own_conversation`, `test_e2e_different_user_same_factory_blocked`, `test_e2e_different_factory_blocked`, `test_e2e_missing_user_context_rejected`.
- **Offline DB-Blocked Tests:**
  - `test_e2e_ingestion_counts` (deselected — requires `operix_db` chunks > 10).
  - `test_e2e_benchmark_evaluator` (62.5% vs 75.0% threshold): `BENCH-01`, `BENCH-02`, `BENCH-03`, `BENCH-05`, `BENCH-06` pass (`100%` refusal honesty); `BENCH-04` (Warehouse PPE Zone), `BENCH-07`, and `BENCH-08` (Restricted Zone Intrusion) fail because `operix_db` ingestion is unavailable offline.
