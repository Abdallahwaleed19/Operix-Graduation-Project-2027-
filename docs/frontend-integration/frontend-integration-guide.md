# Frontend Integration Guide (React / Fetch)

## 1. Base URL Configuration
```javascript
export const API_BASE_URL =
  import.meta?.env?.VITE_API_BASE_URL ||
  process.env.REACT_APP_API_BASE_URL ||
  "http://localhost:8000";
```

## 2. Token & Tenant Headers
Attach `Authorization: Bearer <token>` on every request. Only include `X-Factory-Id` if it matches the factory UUID inside the JWT (mismatches return `403 FORBIDDEN_FACTORY`).

## 3. React Integration Notes
- **Loading & Error States:** Every endpoint returns `{ status: "success", data, meta }` on `2xx` or `{ status: "error", error_code, message, details }` on `4xx`/`5xx`. Always check `!response.ok` and display `err.message`.
- **Evidence Upload:** Read files with `FileReader.readAsDataURL(file)`, strip the `data:*/*;base64,` prefix, and send `{ event_id, kind, file_base64, content_type }`.
- **Evidence / Report Downloads:** Use `fetch()` with the `Authorization` header (do not use `<a href>` directly because Bearer headers cannot be attached to plain links), convert to `await res.blob()`, and trigger download via `URL.createObjectURL(blob)`.
- **RAG Chat:** Store `conversation_id` returned by `POST /api/v1/assistant/ask` in React state and pass it on subsequent turns. Render `proposed_actions` as confirmation buttons that call `POST /api/v1/assistant/actions/execute` with an `idempotency_key`.
