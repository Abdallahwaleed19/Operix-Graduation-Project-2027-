# Known Blockers

1. **Shared Backend `reports.py` (Owner: Seif):** Lines 110, 136, 142 omit `factory_id=user.factory_id` when calling `ReportService.get_report()` and `get_report_file_path()`.
2. **Shared Backend `assistant.py` (Owner: Seif):** Line 165 local fix (`clear_conversation`) awaits explicit Seif approval.
3. **Missing `redis` Package (Environment):** Blocks importing `app.main` (OpenAPI export) and running `backend/tests/test_phase4*.py`.
4. **Offline `operix_db` (Environment / Safety Rule):** Blocks `test_e2e_ingestion_counts`, DB-dependent `BENCH-04/07/08` in `test_e2e_benchmark_evaluator`, `test_ingestion.py` DB loader tests, and live PostgreSQL RLS tests.
