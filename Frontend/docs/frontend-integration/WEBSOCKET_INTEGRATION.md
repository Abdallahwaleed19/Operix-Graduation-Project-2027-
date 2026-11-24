# WebSocket Real-Time Integration Guide

**Frontend Client:** `src/services/websocketService.js`  
**Backend Endpoints:** `backend/app/api/v1/endpoints/websockets.py` & `auth.py`

---

## 1. Authentication Handshake (Phase 2 Ticket Flow)

1. Upon entering `AppLayout` (authenticated state), `websocketService.connect()` runs automatically.
2. Client calls `POST /api/v1/auth/ws-ticket` with `{ factory_id }`.
3. Backend validates JWT + active `FactoryMembership`, stores single-use ticket in Redis with TTL, and returns `{ ticket }`.
4. Client opens native WebSocket connection to:
   `ws://<host>:8000/ws/v2/events?ticket=<ticket>`
5. If `/ws-ticket` is unavailable (e.g., Redis offline in dev), `websocketService` gracefully falls back to:
   `ws://<host>:8000/ws/events?token=<jwt>&factory_id=<uuid>`

---

## 2. Lifecycle, Heartbeat & Reconnection

- **Handshake Confirmation:** Server emits `{ "type": "connection_established", "factory_id": "...", "status": "connected" }`.
- **Heartbeat:** Client sends `{ "type": "ping" }` every **25 seconds**; server responds `{ "type": "pong", "timestamp": "..." }`.
- **Exponential Backoff:** On unexpected socket close (code != `1000`), client reconnects with exponential backoff (`2s`, `4s`, `8s`, `16s`, `30s` max, up to 5 attempts).
- **Clean Teardown:** `AuthContext.logout()` and `AppLayout` unmount invoke `websocketService.disconnect()` (close code `1000`).

---

## 3. Subscribing to Events in Components

```javascript
import { websocketService } from '../services';

useEffect(() => {
  const unsubscribe = websocketService.on('incident_created', (event) => {
    console.log('New real-time safety incident:', event.data);
  });
  return () => unsubscribe();
}, []);
```
