# Seif Required Changes & Approvals (Shared Backend)

## 1. `backend/app/api/v1/endpoints/reports.py` (Required Fix — Not Modified)
- **Lines 110 & 136:** `meta = reports_svc.get_report(report_id)` → must be `meta = reports_svc.get_report(report_id, factory_id=user.factory_id)`
- **Line 142:** `file_path = reports_svc.get_report_file_path(report_id)` → must be `file_path = reports_svc.get_report_file_path(report_id, factory_id=user.factory_id)`
- **Impact:** Without this change, `GET /api/v1/reports/{report_id}` and `GET /api/v1/reports/{report_id}/download` raise `TypeError` at runtime.

## 2. `backend/app/api/v1/endpoints/assistant.py` (Pending Explicit Approval)
- **Line 165:** Local working tree already has `cleared = assistant_svc.clear_conversation(conversation_id, factory_id=user.factory_id, user_id=user.user_id)`.
- **Status:** Preserved in local working tree, **excluded from the AI-owned integration branch commit** per shared-Backend ownership rules until Seif explicitly approves/commits it.
