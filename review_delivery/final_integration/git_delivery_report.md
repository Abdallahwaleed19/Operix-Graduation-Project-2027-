# Git Delivery Plan & Scope

- **Base Commit:** `33aa6e801d6a64bb4042f7159ed72fd950274356` (`main`)
- **Target Integration Branch:** `integration/ai-modules-backend`
- **Remote:** `origin` (no force push, no push to `main`)
- **Included in Commit:** All 24 modified AI-service files, 4 new AI test files, `docs/frontend-integration/` (12 files), and `review_delivery/final_integration/` (16 files).
- **Excluded from Commit:** `backend/app/api/v1/endpoints/assistant.py` (shared Backend file pending Seif approval), `.env`, caches, and `review_handover/` / root `review_delivery/` audit scratch artifacts.
