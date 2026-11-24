/**
 * Operix Frontend API Client Examples (for Toka)
 * Base URL defaults to http://localhost:8000
 */

const API_BASE_URL = "http://localhost:8000";

async function apiRequest(path, { method = "GET", token, body } = {}) {
  const headers = { Authorization: `Bearer ${token}` };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json();
  if (!res.ok || payload.status === "error") {
    const err = new Error(payload.message || `HTTP ${res.status}`);
    err.errorCode = payload.error_code;
    err.details = payload.details;
    throw err;
  }
  return payload.data;
}

// 1. Workforce Analytics Summary
export function fetchWorkforceSummary(token, { startDate, endDate, periodHours = 720 } = {}) {
  const q = new URLSearchParams({ period_hours: String(periodHours) });
  if (startDate) q.set("start_date", startDate);
  if (endDate) q.set("end_date", endDate);
  return apiRequest(`/api/v1/analytics/summary?${q}`, { token });
}

// 2. RAG Safety Assistant Chat
export function askAssistant(token, { question, conversationId = null, language = "auto" }) {
  return apiRequest("/api/v1/assistant/ask", {
    method: "POST",
    token,
    body: {
      question,
      conversation_id: conversationId,
      language_preference: language,
    },
  });
}

// 3. Execute Agentic Remediation Action
export function executeAIAction(token, { actionId, actionType, parameters, idempotencyKey }) {
  return apiRequest("/api/v1/assistant/actions/execute", {
    method: "POST",
    token,
    body: {
      action_id: actionId,
      action_type: actionType,
      parameters,
      idempotency_key: idempotencyKey,
    },
  });
}

// 4. Upload Evidence (Base64)
export function uploadEvidence(token, { eventId, kind = "snapshot", fileBase64, contentType = "image/jpeg", durationS }) {
  return apiRequest("/api/v1/evidence/upload", {
    method: "POST",
    token,
    body: {
      event_id: eventId,
      kind,
      file_base64: fileBase64,
      content_type: contentType,
      duration_s: durationS,
    },
  });
}

// 5. Generate Report
export function generateReport(token, { reportType = "workforce", format = "pdf", dateFrom, dateTo } = {}) {
  return apiRequest("/api/v1/reports/generate", {
    method: "POST",
    token,
    body: {
      report_type: reportType,
      format,
      date_from: dateFrom,
      date_to: dateTo,
    },
  });
}

// 6. Download Binary (Evidence or Report) with Bearer Auth
export async function downloadProtectedFile(path, token, filename) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Download failed: HTTP ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
