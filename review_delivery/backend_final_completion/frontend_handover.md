# Frontend Handover (For Toka)

- **API Documentation:** `docs/frontend-integration/README.md` (12 files covering auth, all 5 AI modules, error handling, React notes, `api-contracts.json`, `frontend-api-examples.js`, and `frontend-integration-checklist.md`).
- **OpenAPI Note:** Runtime `/openapi.json` export from `app.main` is blocked in the offline Python 3.14 audit environment due to missing `redis==8.2.0`; all docs were verified directly from FastAPI routers and Pydantic schemas.
- **Instructions for Toka:**
  1. Pull `main` after merge.
  2. Configure `VITE_API_BASE_URL` / `REACT_APP_API_BASE_URL` (default `http://localhost:8000`).
  3. Attach `Authorization: Bearer <token>` on all `/api/v1/*` calls.
  4. Use `docs/frontend-integration/frontend-api-examples.js` and `frontend-integration-checklist.md` to wire Evidence, Workforce Analytics, RAG Chat, Reports, and AI Actions.
