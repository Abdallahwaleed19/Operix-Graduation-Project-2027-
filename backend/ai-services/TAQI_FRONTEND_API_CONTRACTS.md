# Operix AI Services — Taqi Frontend API Contracts & Integration Guide

**Target Audience:** Taqi (Frontend Lead & Next.js Maintainer)  
**Author:** Abdallah Waleed (AI & Analytical Services Lead)  
**Status:** Validated with Python 3.14, Pydantic v2 & PostgreSQL 18  
**Scope:** Complete frontend integration specifications for Workforce Analytics, LLM/RAG Assistant, Automated Reports, and Incident Evidence.

---

## 1. Global API Conventions

### Base URL & Authentication
- Base URL: `/api/v1`
- All requests must include standard authorization headers:
  ```http
  Authorization: Bearer <jwt_access_token>
  ```
- All responses are wrapped in a standard JSON envelope or return binary streams for file downloads.

### Standard Response Envelope (`OperixResponseEnvelope<T>`)
```typescript
interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data: T;
  timestamp: string; // ISO 8601 UTC
}
```

---

## 2. Module 1: Workforce Analytics Dashboard

### 2.1 Factory Overview
- **Endpoint:** `GET /api/v1/workforce-analytics/overview`
- **Query Parameters:**
  - `factory_id` (UUID, required): Selected factory identifier.
- **Response Type:**
```typescript
interface WorkforceOverviewResponse {
  factory_id: string;
  total_workers: number;
  active_workers: number;
  total_departments: number;
  total_cameras: number;
  active_cameras: number;
  overall_safety_score: number; // 0.0 to 100.0
  period_start: string;
  period_end: string;
}
```

### 2.2 Attendance Metrics (Proxy Metric Notice)
> **UI Notice:** The platform derives presence from camera monitoring and incident logs. Display the proxy disclaimer badge in the attendance widget.

- **Endpoint:** `GET /api/v1/workforce-analytics/attendance`
- **Query Parameters:**
  - `factory_id` (UUID, required)
  - `date_from` (ISO Date `YYYY-MM-DD`, optional)
  - `date_to` (ISO Date `YYYY-MM-DD`, optional)
- **Response Type:**
```typescript
interface AttendanceMetricsResponse {
  factory_id: string;
  date_from: string;
  date_to: string;
  total_expected_workers: number;
  average_daily_presence: number;
  presence_rate_percentage: number;
  daily_breakdown: Array<{
    date: string;
    present_count: number;
    presence_percentage: number;
  }>;
  disclaimer: string; // "Attendance estimated from active system presence and camera detections."
}
```

### 2.3 Incident Analytics & Trends
- **Endpoint:** `GET /api/v1/workforce-analytics/incidents`
- **Query Parameters:**
  - `factory_id` (UUID, required)
  - `date_from` (ISO Date, optional)
  - `date_to` (ISO Date, optional)
- **Response Type:**
```typescript
interface IncidentAnalyticsResponse {
  factory_id: string;
  total_incidents: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  by_state: {
    open: number;
    investigating: number;
    resolved: number;
    dismissed: number;
  };
  mean_time_to_review_minutes: number;
  mean_time_to_resolve_minutes: number;
  resolution_rate_percentage: number;
}
```

### 2.4 Camera Coverage & Blind Spots
- **Endpoint:** `GET /api/v1/workforce-analytics/camera-coverage`
- **Query Parameters:**
  - `factory_id` (UUID, required)
- **Response Type:**
```typescript
interface CameraCoverageResponse {
  factory_id: string;
  total_cameras: number;
  active_cameras: number;
  coverage_percentage: number;
  unobserved_gaps_count: number;
  per_camera_status: Array<{
    camera_id: string;
    name: string;
    status: "active" | "inactive" | "maintenance" | "offline";
    department_name: string | null;
  }>;
  unobserved_gaps: Array<{
    gap_id: string;
    camera_id: string;
    started_at: string;
    ended_at: string | null;
    reason: string;
  }>;
}
```

---

## 3. Module 2: AI Safety Assistant & Agentic Remediation

### 3.1 Conversational Safety Query
- **Endpoint:** `POST /api/v1/rag-assistant/chat`
- **Request Body (`application/json`):**
```typescript
interface ChatMessageRequest {
  message: string;             // e.g. "What PPE is required in the welding area?"
  factory_id?: string;         // Scope retrieval to factory tenant SOPs
  department_id?: string;      // Optional department filter
  conversation_history?: Array<{
    role: "user" | "assistant" | "system";
    content: string;
  }>;
}
```
- **Response Body:**
```typescript
interface ChatMessageResponse {
  answer: string;              // Markdown-formatted response with Arabic & English support
  citations: Array<{
    source_id: string;
    source_title: string;
    source_type: string;
    snippet: string;
    confidence_score: number;
  }>;
  proposed_actions: Array<{    // Agentic remediation proposals requiring user confirmation
    action_id: string;
    action_type: "maintenance" | "alert" | "escalation" | "policy_review";
    title: string;
    description: string;
    parameters: Record<string, any>;
    requires_confirmation: boolean;
  }>;
}
```

### 3.2 Executing Remediation Actions
When the supervisor clicks "Approve Action" in the UI:
- **Endpoint:** `POST /api/v1/rag-assistant/execute-action`
- **Headers:**
  - `X-Idempotency-Key`: Client-generated UUID to prevent double-clicking or duplicated dispatches.
- **Request Body:**
```typescript
interface ActionExecutionRequest {
  action_id: string;
  action_type: string;
  parameters: Record<string, any>;
  factory_id?: string;
  confirmed_by?: string;      // User display name or ID
  user_role?: "operator" | "supervisor" | "factory_manager";
}
```
- **Response Body:**
```typescript
interface ActionExecutionResponse {
  action_id: string;
  status: "executed" | "rejected";
  message: string;
  audit_reference: string;    // e.g. "AUDIT-20261122-C842B1"
  details: Record<string, any>;
}
```

---

## 4. Module 3: Automated Reports Generation

### 4.1 Requesting a Report
- **Endpoint:** `POST /api/v1/reports/generate`
- **Request Body:**
```typescript
interface ReportGenerationRequest {
  factory_id: string;
  report_type: "workforce" | "incident" | "camera_coverage" | "comprehensive_safety";
  format: "pdf" | "excel" | "json";
  date_from?: string; // "YYYY-MM-DD"
  date_to?: string;   // "YYYY-MM-DD"
}
```
- **Response Body:**
```typescript
interface ReportGenerationResponse {
  report_id: string;          // e.g. "REP-20261122-F677B9"
  factory_id: string;
  report_type: string;
  format: "pdf" | "excel" | "json";
  status: "completed" | "failed";
  download_url: string;       // Direct download URL: "/api/v1/reports/download/..."
  file_size_bytes: number;
  generated_at: string;
  disclaimer: string;
}
```

### 4.2 Report Download
- Trigger browser download directly from `download_url`:
  ```typescript
  const handleDownload = (downloadUrl: string, filename: string) => {
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  ```

---

## 5. Module 4: Incident Evidence Recording & Retrieval

### 5.1 Evidence File Upload (`multipart/form-data`)
> **Important Database Rules:**
> - Supported kinds: `snapshot` (images: PNG, JPEG, WEBP) and `clip` (videos: MP4, WebM, AVI, MKV).
> - Audio uploads are **not supported** by the database schema and will be rejected with HTTP 400.
> - For video clips, `duration_s` is **mandatory** and must be an integer $> 0$.

- **Endpoint:** `POST /api/v1/evidence/upload`
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `factory_id` (UUID, required): Factory ID
  - `event_id` (UUID, required): Associated safety event ID
  - `file` (Binary File, required): Image or video file
  - `duration_s` (Integer, required for videos, omit for snapshots): Length of clip in seconds
  - `captured_at` (ISO 8601 string, optional): When media was captured
  - `expires_at` (ISO 8601 string, optional): Data retention expiry timestamp

**Example Upload Handler in Next.js:**
```typescript
async function uploadEvidence(
  factoryId: string,
  eventId: string,
  file: File,
  durationSeconds?: number
) {
  const formData = new FormData();
  formData.append("factory_id", factoryId);
  formData.append("event_id", eventId);
  formData.append("file", file);

  if (file.type.startsWith("video/")) {
    if (!durationSeconds || durationSeconds <= 0) {
      throw new Error("Duration in seconds is required for video clips.");
    }
    formData.append("duration_s", durationSeconds.toString());
  }

  const response = await fetch("/api/v1/evidence/upload", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.message || "Failed to upload evidence.");
  }

  return await response.json();
}
```

- **Upload Response Body:**
```typescript
interface EvidenceUploadResponse {
  evidence_id: string;        // UUID of the created evidence record
  factory_id: string;
  event_id: string;
  kind: "snapshot" | "clip";
  storage_key: string;       // e.g. "f/aaaa-0001/.../uuid.png"
  content_type: string;
  size_bytes: number;
  sha256: string;            // SHA-256 fingerprint for forensic chain-of-custody
  duration_s: number | null;
  captured_at: string;
  created_at: string;
}
```

### 5.2 Retrieving Evidence List for an Event
- **Endpoint:** `GET /api/v1/evidence/by-event/{event_id}`
- **Query Parameters:**
  - `factory_id` (UUID, required)
- **Response Body:**
```typescript
interface EvidenceListResponse {
  event_id: string;
  factory_id: string;
  total_count: number;
  items: Array<{
    id: string;
    factory_id: string;
    event_id: string;
    kind: "snapshot" | "clip";
    content_type: string;
    size_bytes: number;
    sha256: string;
    duration_s: number | null;
    captured_at: string;
    download_url: string; // "/api/v1/evidence/{id}/download?factory_id=..."
  }>;
}
```

### 5.3 Streaming Evidence Media (Images & Videos)
- Use standard `<img src="/api/v1/evidence/{id}/download?factory_id=..." />` or `<video src="..." controls />`.
- The endpoint supports HTTP streaming and range requests for seeking within video clips.

### 5.4 Forensic Cryptographic Verification
Display an "Audit Chain of Custody" modal that verifies the stored file matches its original SHA-256 hash:
- **Endpoint:** `GET /api/v1/evidence/{evidence_id}/integrity`
- **Query Parameters:** `factory_id` (UUID, required)
- **Response Body:**
```typescript
interface EvidenceIntegrityResponse {
  evidence_id: string;
  stored_sha256: string;
  computed_sha256: string;
  is_intact: boolean;
  verified_at: string;
  message: string; // "Integrity verified: SHA-256 matches."
}
```
