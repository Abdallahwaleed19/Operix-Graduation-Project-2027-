# Authentication & Tenant Context

**Source Files:**
- `backend/app/api/deps.py` (`get_current_user_context`, `get_current_factory_id`, `AuthenticatedUser`)
- `backend/app/api/v1/endpoints/auth.py` (`POST /api/v1/auth/ws-ticket`)

---

## 1. Required HTTP Headers

Every AI endpoint uses `Depends(get_current_user_context)` and expects:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Optional tenant header:
```http
X-Factory-Id: <factory_uuid>
```

### Rules Enforced by `get_current_user_context`
1. Missing or malformed `Authorization: Bearer <token>` returns `401` (`MISSING_AUTH_HEADER` / `INVALID_TOKEN`) in production.
2. Token `sub` claim must be a valid user UUID; `factory_id` claim is extracted from the JWT.
3. If both JWT `factory_id` and `X-Factory-Id` header are sent and they do not match, the backend rejects with `403` (`FORBIDDEN_FACTORY`).
4. Never send `user_id` or `factory_id` inside request bodies to override identity — the backend derives `AuthenticatedUser` from the verified token.

---

## 2. Issue One-Time WebSocket Ticket

- **Method & Path:** `POST /api/v1/auth/ws-ticket`
- **Status:** Implemented and registered
- **Auth:** `Authorization: Bearer <token>`

### Request Body (`WsTicketRequest`)
```json
{
  "factory_id": "aaaaaaaa-0001-0001-0001-000000000001"
}
```

### Success Response (`200 OK`)
```json
{
  "status": "success",
  "data": {
    "ticket": "<signed_one_time_ticket>",
    "expires_at": 1795550030,
    "expires_in_seconds": 30,
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001"
  },
  "meta": {
    "request_timestamp": "2026-11-24T19:50:00Z",
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "api_version": "v1"
  }
}
```

### JavaScript Example
```javascript
const res = await fetch(`${API_BASE_URL}/api/v1/auth/ws-ticket`, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ factory_id: factoryId }),
});
```
