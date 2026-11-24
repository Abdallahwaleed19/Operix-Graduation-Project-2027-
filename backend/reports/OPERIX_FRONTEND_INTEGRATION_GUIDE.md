# OPERIX — FRONTEND INTEGRATION GUIDE
## Safety Rule Builder & Real-Time Event Dashboard

**Target Audience:** Frontend Engineering Team (Toka)  
**Status:** APPROVED & TESTED  
**Version:** 2.0.0 (Phase 4 Final Acceptance)  

---

## 1. Authentication & Tenant Headers

Every HTTP API request made from the frontend to `/api/v1/rules` or `/api/v1/events` requires two headers:
1. `Authorization: Bearer <access_token>` (Standard JWT received at login).
2. `X-Factory-Id: <factory_uuid>` (The active factory selected in the factory switcher).

### Connecting to the Real-Time WebSocket (`/ws/events`):
WebSockets do **not** accept raw long-lived JWTs. You must exchange your JWT for a single-use, 30-second **WS Ticket**:
1. Call `POST /api/v1/auth/ws-ticket` with body `{"factory_id": "<factory_uuid>"}`.
2. Receive response `{ "status": "success", "data": { "ticket": "<short_lived_ticket>" } }`.
3. Open WebSocket connection: `wss://<host>/ws/events?ticket=<short_lived_ticket>`.
4. The ticket is atomically consumed on connection; reconnects require fetching a fresh ticket.

---

## 2. Safety Rule Builder UI Implementation

### 2.1 Displaying the Rule List
- **Endpoint:** `GET /api/v1/rules`
- **Query Params:**
  - `is_enabled` (optional boolean, e.g. `?is_enabled=true`)
  - `event_type` (optional string, e.g. `?event_type=ppe_violation`)
  - `limit` (default: 50, max: 200)
  - `offset` (default: 0)
- **UI Component Suggestions:**
  - Table showing: Rule Name, Event Type, Scope (Global, Zone, Department, Sensor), Severity Badge, Minimum Confidence, Notification Toggle, Active Switch.
- **Example Response:**
  ```json
  {
    "status": "success",
    "data": {
      "items": [
        {
          "id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
          "name": "Strict Hardhat Rule",
          "event_type": "ppe_violation",
          "severity": "critical",
          "zone_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
          "department_id": null,
          "sensor_id": null,
          "min_confidence": 0.85,
          "min_duration_s": 2,
          "threshold_value": null,
          "notify": true,
          "is_enabled": true,
          "version": 3,
          "created_at": "2026-11-23T20:00:00Z",
          "updated_at": "2026-11-23T20:45:00Z"
        }
      ],
      "total": 1
    }
  }
  ```

### 2.2 Rule Creation Modal / Form
- **Endpoint:** `POST /api/v1/rules`
- **Scope Selector Rule (Crucial):**
  The UI form must ensure the user selects **at most one scope type**:
  - `Global`: Do not pass `zone_id`, `department_id`, or `sensor_id` (leave `null`).
  - `Zone`: Pass selected `zone_id` (leave department and sensor `null`).
  - `Department`: Pass selected `department_id` (leave zone and sensor `null`).
  - `Sensor`: Pass selected `sensor_id` (leave zone and department `null`).
- **Allowed Event Types:**
  - `ppe_violation` (PPE Violation)
  - `fall` (Worker Fall)
  - `restricted_zone_intrusion` (Restricted Zone Entry)
  - `potential_fatigue` (Fatigue Detection)
  - `fire` (Fire Detection)
  - `smoke` (Smoke Detection)
  - `temperature_anomaly` (Sensor Temperature Alert)
  - `source_failure` (Camera/Sensor Failure)
- **Severity Levels:**
  - `low`, `medium`, `high`, `critical`

### 2.3 Rule Active Toggle Switch
- **Endpoint:** `PATCH /api/v1/rules/{rule_id}/status`
- **Body:** `{"is_enabled": true}` or `{"is_enabled": false}`
- Immediate feedback: Updates the rule without incrementing the rule's version or resetting other fields.

### 2.4 Editing a Rule
- **Endpoint:** `PUT /api/v1/rules/{rule_id}`
- Send updated fields. Every update automatically increments `version` by 1.
- To convert a previously zone-scoped rule into a factory-wide global rule, pass:
  ```json
  {
    "zone_id": null,
    "clear_scope": true
  }
  ```

### 2.5 Deleting a Rule
- **Endpoint:** `DELETE /api/v1/rules/{rule_id}`
- Triggers a confirmation dialog.
- Past events that triggered this rule will remain visible in the dashboard; their `rule_id` foreign key is safely set to null in the database.

---

## 3. Real-Time Safety Event Stream (WebSocket)

When listening on `/ws/events`, the backend streams live events as detections occur.

### Incoming Packet Structure:
```typescript
interface SafetyEventPacket {
  type: "safety_event";
  factory_id: string;
  data: {
    event_id: string;
    event_type: "ppe_violation" | "fall" | "restricted_zone_intrusion" | "potential_fatigue" | "fire" | "smoke" | "temperature_anomaly" | "source_failure";
    event_state: "started" | "ongoing" | "ended";
    module: string;
    camera_id: string;
    timestamp: string; // ISO 8601 UTC
    confidence: number;
    track_id: number | null;
    bbox_normalized: [number, number, number, number] | null; // [x, y, w, h] normalized 0.0 - 1.0
    rule_id: string | null;      // Primary matched SafetyRule ID
    incident_id: string | null;  // Associated Incident ID if correlated
    should_notify: boolean;      // True if any matched rule triggers notification
    details: {
      module: string;
      raw_camera_tag: string;
      frame_index?: number;
      missing?: string[];
      rule_evaluation?: {
        status: "evaluated" | "no_rules_configured";
        evaluated_count: number;
        matched_count: number;
        matched_rule_ids: string[];
        highest_severity: "low" | "medium" | "high" | "critical" | null;
        should_notify: boolean;
        primary_rule_id: string | null;
      };
      [key: string]: any;
    };
  };
  sent_at: string;
}
```

### Dashboard Rendering Guidelines:
1. **Critical Alert Banners:** If `data.should_notify === true`, immediately display an alert banner or sound an alert tone.
2. **Bounding Box Video Overlay:** Use `data.bbox_normalized` (`[x, y, w, h]`) directly on video player canvas elements:
   - $X_{pixel} = x \times W_{video}$
   - $Y_{pixel} = y \times H_{video}$
   - $Width_{pixel} = w \times W_{video}$
   - $Height_{pixel} = h \times H_{video}$
3. **Severity Styling:** Use the severity from `data.details.rule_evaluation.highest_severity`:
   - `critical`: Red (`#EF4444`)
   - `high`: Orange (`#F97316`)
   - `medium`: Yellow (`#F59E0B`)
   - `low`: Blue/Gray (`#3B82F6`)

---

## 4. Standard Error Handling

All backend errors follow a uniform JSON structure:
```json
{
  "status": "error",
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "SafetyRule with ID 'c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a' not found.",
  "timestamp": "2026-11-23T20:10:00Z"
}
```

### Common Error Codes:
- `VALIDATION_ERROR` (400): Scope exclusivity violation or invalid parameters.
- `UNAUTHORIZED` (401): Missing or expired authentication token.
- `FORBIDDEN` (403): User lacks membership in the requested factory.
- `RESOURCE_NOT_FOUND` (404): Rule, zone, or department does not exist in the tenant.
- `INTERNAL_SERVER_ERROR` (500): Unhandled exception.

---

## 5. Phase 4 AI Services & Copilot Integration

### 5.1 Workforce Analytics Endpoints
- **Base Path:** `/api/v1/analytics`
- **Headers:** `Authorization: Bearer <token>`, `X-Factory-Id: <factory_uuid>`
- **Endpoints:**
  - `GET /overview` — High-level workforce & safety KPI summary (total workers, attendance rate, total incidents, average compliance score).
  - `GET /attendance` — Daily/hourly attendance trends (`?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`).
  - `GET /incidents` — Incident breakdown by severity, zone, and time series.
  - `GET /productivity` — Department productivity and compliance correlations.
  - `GET /camera-coverage` — Camera uptime and monitoring coverage health.
  - `GET /summary` — Executive multi-dimensional safety summary.

### 5.2 Copilot / LLM Assistant Endpoints
- **Base Path:** `/api/v1/assistant`
- **Headers:** `Authorization: Bearer <token>`, `X-Factory-Id: <factory_uuid>`
- **Endpoints:**
  - `POST /ask` — Ask natural-language safety questions. Returns answers with grounded sources and recommended actions.
    ```json
    {
      "question": "What are the hardhat violation procedures for Zone B?",
      "conversation_id": "optional-uuid"
    }
    ```
    Response includes `answer`, `confidence`, `sources`, `suggested_actions`, and `conversation_id`.
  - `POST /actions/execute` — Execute Copilot-recommended actions with role authorization.
    ```json
    {
      "action_type": "acknowledge_incident",
      "target_id": "11111111-1111-1111-1111-111111111111",
      "parameters": { "reason": "Operator cleared zone" },
      "idempotency_key": "unique-client-uuid"
    }
    ```
    Supported `action_type`: `create_incident`, `acknowledge_incident`, `request_alert`, `sensor_toggle`, `maintenance`, `dispatch`, `escalation`.
  - `GET /sources` — List indexed safety policies and standard operating procedures.
  - `GET /conversations/{id}` — Retrieve assistant chat history.
  - `GET /health` — Assistant and vector store health check.

### 5.3 Reports Generation Endpoints
- **Base Path:** `/api/v1/reports`
- **Headers:** `Authorization: Bearer <token>`, `X-Factory-Id: <factory_uuid>`
- **Endpoints:**
  - `POST /generate` — Generate report on demand (PDF, Excel, HTML, JSON).
    ```json
    {
      "report_type": "safety_compliance",
      "format": "pdf",
      "start_date": "2026-11-01T00:00:00Z",
      "end_date": "2026-11-24T00:00:00Z"
    }
    ```
  - `GET ""` — List generated reports for the factory with pagination.
  - `GET /{id}` — Retrieve report status and metadata.
  - `GET /{id}/download` — Secure binary download with `Content-Disposition`.

### 5.4 Incident Evidence Endpoints
- **Base Path:** `/api/v1/evidence`
- **Headers:** `Authorization: Bearer <token>`, `X-Factory-Id: <factory_uuid>`
- **Endpoints:**
  - `POST /upload` — Upload evidence file (image/video/log) via Base64 JSON:
    ```json
    {
      "incident_id": "11111111-1111-1111-1111-111111111111",
      "filename": "camera_zone_b_violation.jpg",
      "file_base64": "<base64_encoded_content>",
      "content_type": "image/jpeg"
    }
    ```
  - `GET ""` — List evidence files for authorized incidents (`?incident_id=<uuid>`).
  - `GET /{id}` — Retrieve evidence metadata, SHA-256 hash, and byte size.
  - `GET /{id}/download` — Download evidence binary.
  - `GET /{id}/verify-integrity` — Verify SHA-256 integrity hash against file on disk.

### 5.5 AI Action WebSocket Events
When an action is executed via `/api/v1/assistant/actions/execute`, events are broadcast in real-time over the existing WebSocket connection (`/ws/events?ticket=...`):
- `incident_created`: When `create_incident` is called.
- `alert_created`: When `request_alert` is called.
- `ai_action_completed`: Broadcast for all successful action executions:
  ```json
  {
    "event_type": "ai_action_completed",
    "factory_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "payload": {
      "action_type": "acknowledge_incident",
      "target_id": "11111111-1111-1111-1111-111111111111",
      "status": "success",
      "executed_by": "user-uuid"
    },
    "sent_at": "2026-11-24T16:00:00Z"
  }
  ```
