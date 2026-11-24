# OPERIX — PHASE 3 API CONTRACT SPECIFICATION
## Safety Rule Builder & Event Ingestion Endpoints

**Status:** APPROVED & TESTED  
**Version:** 1.0.0 (Phase 3.6 Final)  
**Base Path:** `/api/v1`  
**Security:** JWT Bearer (Factory Context) or API Key (`X-Camera-Key`)  

---

## 1. Safety Rule Builder Endpoints (`/api/v1/rules`)

All endpoints in this group require authenticated tenant user access (JWT Bearer Token with active `FactoryMembership` and `X-Factory-Id` header).

### 1.1 Create Safety Rule
- **Method:** `POST`
- **URL:** `/api/v1/rules`
- **Authentication:** `Bearer <JWT_TOKEN>` + Header `X-Factory-Id: <UUID>`
- **Permissions:** Admin, Safety Supervisor
- **Request Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
  - `X-Factory-Id: <UUID>`
- **Request Body (`SafetyRuleCreate`):**
  ```json
  {
    "name": "Strict Assembly PPE Rule",
    "event_type": "ppe_violation",
    "severity": "high",
    "zone_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "department_id": null,
    "sensor_id": null,
    "min_confidence": 0.85,
    "min_duration_s": 3,
    "threshold_value": null,
    "notify": true,
    "is_enabled": true
  }
  ```
- **Validation Rules:**
  - `name`: 1–120 characters, non-empty.
  - `event_type`: Valid `EventType` (`ppe_violation`, `fall`, `restricted_zone_intrusion`, `potential_fatigue`, `fire`, `smoke`, `temperature_anomaly`, `source_failure`).
  - `severity`: `low`, `medium`, `high`, `critical`.
  - **Scope Exclusivity:** At most one of `zone_id`, `department_id`, or `sensor_id` may be non-null. If all are null, the rule is **global** to the factory.
  - `min_confidence`: Optional, float between `0.0` and `1.0`.
  - `min_duration_s`: Optional, integer $\ge 0$.
  - `threshold_value`: Optional decimal number.
- **Success Response:** `201 Created`
  ```json
  {
    "status": "success",
    "data": {
      "id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "Strict Assembly PPE Rule",
      "event_type": "ppe_violation",
      "severity": "high",
      "zone_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "department_id": null,
      "sensor_id": null,
      "min_confidence": 0.85,
      "min_duration_s": 3,
      "threshold_value": null,
      "notify": true,
      "is_enabled": true,
      "version": 1,
      "created_at": "2026-11-23T20:00:00Z",
      "updated_at": "2026-11-23T20:00:00Z"
    },
    "meta": {
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "api_version": "v1"
    }
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Scope exclusivity violated (`"At most one of zone_id, department_id, or sensor_id may be specified"`).
  - `401 Unauthorized`: Missing or invalid Bearer token.
  - `404 Not Found`: Referent `zone_id`, `department_id`, or `sensor_id` does not exist or belongs to another factory.
  - `422 Unprocessable Content`: Field validation error (e.g. `min_confidence` > 1.0).

---

### 1.2 List Safety Rules
- **Method:** `GET`
- **URL:** `/api/v1/rules`
- **Query Parameters:**
  - `is_enabled` (optional, boolean): Filter by active status (`true` / `false`).
  - `event_type` (optional, string): Filter by target event type (`ppe_violation`, etc.).
  - `limit` (optional, integer, default: 50, min: 1, max: 200): Maximum records to return.
  - `offset` (optional, integer, default: 0, min: 0): Pagination offset.
- **Success Response:** `200 OK`
  ```json
  {
    "status": "success",
    "data": {
      "items": [
        {
          "id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
          "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
          "name": "Strict Assembly PPE Rule",
          "event_type": "ppe_violation",
          "severity": "high",
          "zone_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
          "department_id": null,
          "sensor_id": null,
          "min_confidence": 0.85,
          "min_duration_s": 3,
          "threshold_value": null,
          "notify": true,
          "is_enabled": true,
          "version": 1,
          "created_at": "2026-11-23T20:00:00Z",
          "updated_at": "2026-11-23T20:00:00Z"
        }
      ],
      "total": 1
    },
    "meta": {
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    }
  }
  ```

---

### 1.3 Get Safety Rule by ID
- **Method:** `GET`
- **URL:** `/api/v1/rules/{rule_id}`
- **Path Parameters:** `rule_id` (UUID)
- **Success Response:** `200 OK` (Single `SafetyRuleResponse`)
- **Error Responses:**
  - `404 Not Found`: Rule not found or belongs to a different factory tenant.

---

### 1.4 Update Safety Rule
- **Method:** `PUT`
- **URL:** `/api/v1/rules/{rule_id}`
- **Path Parameters:** `rule_id` (UUID)
- **Request Body (`SafetyRuleUpdate`):**
  Supports full or partial updates. Automatically increments `rule.version` by 1.
  ```json
  {
    "name": "Updated Strict Assembly PPE Rule",
    "min_confidence": 0.90,
    "clear_scope": false
  }
  ```
  *(Note: Pass `"clear_scope": true` to reset a scoped rule to factory-global scope).*
- **Success Response:** `200 OK` (Updated `SafetyRuleResponse` with incremented `version`).
- **Error Responses:**
  - `400 Bad Request`: Scope exclusivity violated.
  - `404 Not Found`: Rule not found in current factory.

---

### 1.5 Update Safety Rule Status (Toggle Active State)
- **Method:** `PATCH`
- **URL:** `/api/v1/rules/{rule_id}/status`
- **Path Parameters:** `rule_id` (UUID)
- **Request Body (`SafetyRuleStatusUpdate`):**
  ```json
  {
    "is_enabled": false
  }
  ```
- **Success Response:** `200 OK` (Reflects updated `is_enabled` state).

---

### 1.6 Delete Safety Rule
- **Method:** `DELETE`
- **URL:** `/api/v1/rules/{rule_id}`
- **Path Parameters:** `rule_id` (UUID)
- **Behavior:** Safely deletes the rule. Events historically referencing this rule remain preserved; database foreign key `events.rule_id` automatically sets to `NULL` (`ON DELETE SET NULL`).
- **Success Response:** `200 OK`
  ```json
  {
    "status": "success",
    "data": {
      "deleted": true,
      "rule_id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a"
    },
    "meta": {
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
    }
  }
  ```

---

## 2. Event Ingestion Endpoints (`/api/v1/events`)

Ingestion endpoints require authentication via the camera producer API key.

### 2.1 Ingest Single Event
- **Method:** `POST`
- **URL:** `/api/v1/events/ingest`
- **Authentication:** Header `X-Camera-Key: <CV_API_KEY>`
- **Request Body (`CVEventIngest`):**
  ```json
  {
    "event_id": "8f3e2d1c-4b5a-6e7f-8a9b-0c1d2e3f4a5b",
    "event_type": "ppe_violation",
    "event_state": "started",
    "module": "ppe_detection",
    "camera_id": "cam_assembly_01",
    "timestamp": "2026-11-23T20:15:30Z",
    "frame_index": 1542,
    "frame_size": [2304, 1296],
    "bbox": [576.0, 324.0, 1152.0, 648.0],
    "track_id": 4,
    "confidence": 0.92,
    "attributes": {
      "missing": ["helmet", "vest"]
    }
  }
  ```
- **Success Response:** `201 Created`
  ```json
  {
    "status": "success",
    "data": {
      "event_id": "8f3e2d1c-4b5a-6e7f-8a9b-0c1d2e3f4a5b",
      "status": "ingested",
      "event_type": "ppe_violation",
      "broadcast": true,
      "persisted": true,
      "rule_id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
      "matched_rules_count": 1,
      "should_notify": true
    },
    "meta": {
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "api_version": "v1"
    }
  }
  ```
- **Idempotent Duplicate Response:** `201 Created`
  *(When the same `event_id` is re-sent)*
  ```json
  {
    "status": "success",
    "data": {
      "event_id": "8f3e2d1c-4b5a-6e7f-8a9b-0c1d2e3f4a5b",
      "status": "duplicate_ignored",
      "event_type": "ppe_violation",
      "broadcast": false,
      "persisted": true,
      "rule_id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
      "matched_rules_count": 0,
      "should_notify": false
    },
    "meta": {
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "api_version": "v1"
    }
  }
  ```

---

### 2.2 Batch Event Ingestion (`/api/v1/events/batch`)
- **Method:** `POST`
- **URL:** `/api/v1/events/batch`
- **Authentication:** Header `X-Camera-Key: <CV_API_KEY>`
- **Request Body (`CVFrameResultIngest`):**
  Accepts a complete frame analysis payload containing multiple detection bboxes and multiple safety events emitted from that frame.
- **Success Response:** `201 Created` (`EventBatchIngestResponse`)
  ```json
  {
    "status": "success",
    "data": {
      "total_received": 2,
      "ingested_count": 2,
      "duplicates_count": 0,
      "events": [
        {
          "event_id": "8f3e2d1c-4b5a-6e7f-8a9b-0c1d2e3f4a5b",
          "status": "ingested",
          "event_type": "ppe_violation",
          "broadcast": true,
          "persisted": true,
          "rule_id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
          "matched_rules_count": 1,
          "should_notify": true
        }
      ]
    },
    "meta": {
      "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "api_version": "v1"
    }
  }
  ```

---

## 3. Real-Time WebSocket Event Contract (`/ws/events`)

Clients authenticated with a short-lived WS Ticket receive live events partitioned by `factory_id`.

- **Event Packet Format:**
  ```json
  {
    "type": "safety_event",
    "factory_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "data": {
      "event_id": "8f3e2d1c-4b5a-6e7f-8a9b-0c1d2e3f4a5b",
      "event_type": "ppe_violation",
      "event_state": "started",
      "module": "ppe_detector",
      "camera_id": "cam_assembly_01",
      "timestamp": "2026-11-23T20:15:30Z",
      "confidence": 0.92,
      "track_id": 4,
      "bbox_normalized": [0.25, 0.25, 0.25, 0.25],
      "rule_id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
      "incident_id": null,
      "should_notify": true,
      "details": {
        "module": "ppe_detector",
        "missing": ["helmet"],
        "rule_evaluation": {
          "status": "evaluated",
          "evaluated_count": 3,
          "matched_count": 1,
          "matched_rule_ids": ["c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a"],
          "highest_severity": "high",
          "should_notify": true,
          "primary_rule_id": "c3d9b4b0-4f5a-4e89-a2e6-7b8c9d0e1f2a",
          "incident_id": null
        }
      }
    },
    "sent_at": "2026-11-23T20:15:30.150Z"
  }
  ```
