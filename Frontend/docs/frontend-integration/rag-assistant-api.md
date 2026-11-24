# LLM / RAG Safety Assistant API

**Router File:** `backend/app/api/v1/endpoints/assistant.py`  
**Router Prefix:** `/api/v1/assistant`  
**Auth:** All endpoints require `Depends(get_current_user_context)`.

---

## 1. Ask Safety Assistant
- **Endpoint:** `POST /api/v1/assistant/ask`
- **Status:** Implemented and registered (`200 OK`)
- **Request Body (`AssistantQueryIn`):**
  - `question` (string, 2..1000 chars, required — Arabic or English)
  - `conversation_id` (string, optional)
  - `language_preference` (`"auto"` | `"ar"` | `"en"`, default `"auto"`)
  - *Note:* `user_context` in `AssistantQueryIn` is ignored/overwritten server-side with `AuthenticatedUser`.

```json
{
  "question": "What are the PPE rules in the welding area?",
  "conversation_id": null,
  "language_preference": "auto"
}
```

### Success Response (`200 OK`)
```json
{
  "status": "success",
  "data": {
    "answer": "Mandatory helmet, welding visor, and flame-resistant gloves...",
    "conversation_id": "conv-12345678",
    "has_sufficient_evidence": true,
    "citations": [
      {
        "source_title": "PPE Violation — Welding",
        "source_type": "manual_markdown",
        "source_id": "ppe_welding.md",
        "snippet": "...",
        "similarity_score": 0.89
      }
    ],
    "proposed_actions": []
  },
  "meta": {
    "factory_id": "aaaaaaaa-0001-0001-0001-000000000001",
    "api_version": "v1"
  }
}
```

---

## 2. Retrieve Source Citations
- **Endpoint:** `GET /api/v1/assistant/sources?q=<query>`
- **Status:** Implemented and registered (`200 OK`)
- **Query Param:** `q` (string, min length `2`, required)

---

## 3. Clear Conversation History
- **Endpoint:** `DELETE /api/v1/assistant/conversations/{conversation_id}`
- **Status:** Implemented and registered (`200 OK`, returns `403 TENANT_ACCESS_DENIED` on cross-user/cross-factory access per Seif commit `cdda98c`).

---

## 4. Assistant Health Check
- **Endpoint:** `GET /api/v1/assistant/health`
- **Status:** Implemented and registered (`200 OK`)
