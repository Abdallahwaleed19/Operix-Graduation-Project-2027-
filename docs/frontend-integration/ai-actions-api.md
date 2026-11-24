# AI Actions Execution API

**Router File:** `backend/app/api/v1/endpoints/assistant.py`  
**Service File:** `backend/app/services/ai_action_service.py` (`AIActionService`)  
**Status:** Implemented and registered (`200 OK`)

---

## Execute Agentic Remediation Action

- **Method & Path:** `POST /api/v1/assistant/actions/execute`
- **Auth & DB:** `Depends(get_current_user_context)`, `Depends(get_tenant_db)`, `Depends(get_ai_action_service)`
- **WebSocket:** Stages `incident_created`, `alert_created`, and `ai_action_completed` events and broadcasts post-commit via `BackgroundTasks`.

### Supported `action_type` Values
- **Privileged (blocked for `operator` / `worker` with `403 INSUFFICIENT_PERMISSIONS`):**
  `create_incident`, `alert`, `request_alert`, `sensor_toggle`, `mute_sensor`, `escalation`
- **Standard:**
  `acknowledge_incident`, `investigate_incident`, `maintenance`, `dispatch`

### Request Body (`ActionExecutionIn`)
```json
{
  "action_id": "ACT-001",
  "action_type": "acknowledge_incident",
  "parameters": {
    "incident_id": "22222222-2222-2222-2222-222222222222"
  },
  "confirmed_by": "Supervisor Ali",
  "idempotency_key": "idem-act-001"
}
```

### Parameter Requirements by Action Type
- `acknowledge_incident`, `investigate_incident`, `alert`, `request_alert`: requires `parameters.incident_id` (UUID).
- `sensor_toggle`, `mute_sensor`: requires `parameters.sensor_id` (UUID) and optional `parameters.status`.
- `create_incident`: optional `incident_type`, `severity`, `description`.

### Success Response (`200 OK`)
```json
{
  "status": "success",
  "data": {
    "action_id": "ACT-001",
    "status": "executed",
    "message": "Incident 22222222-... acknowledged and state set to 'under_review'.",
    "audit_reference": "AUDIT-20261124-A1B2C3",
    "details": {
      "incident_id": "22222222-2222-2222-2222-222222222222",
      "state": "under_review"
    },
    "execution_timestamp": "2026-11-24T19:50:00+00:00"
  },
  "meta": {
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "api_version": "v1"
  }
}
```
