# Remaining Blockers & Environment Limitations

1. **Missing `redis==8.2.0` in Local Python 3.14 Audit Environment:**
   - Blocks importing `app.main` (live `/openapi.json` export) and running `backend/tests/` (`test_phase42_ai_routers.py` and the 203 Backend offline tests).
   - **Action:** Run `pip install -r backend/requirements.txt` in the target runtime/CI environment before running Backend HTTP tests.
2. **Offline `operix_db` Policy:**
   - Live PostgreSQL (`operix_db`) was never accessed per safety rules; therefore, `test_e2e_ingestion_counts`, DB-dependent `BENCH-04/07/08` in `test_e2e_benchmark_evaluator`, and `workforce_analytics` live DB tests (51 skipped) remain unverified against live PostgreSQL.
